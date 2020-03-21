# -*- coding: utf-8 -*-
from __future__ import absolute_import

import pytz
from datetime import datetime
from exam import fixture

from django.core import mail
from django.utils import timezone

from sentry.digests.notifications import build_digest, event_to_record
from sentry.event_manager import get_event_type, EventManager
from sentry.models import (
    OrganizationMember,
    OrganizationMemberTeam,
    ProjectOwnership,
    ProjectOption,
    Repository,
    Rule,
    UserOption,
)
from sentry.ownership.grammar import Owner, Matcher, dump_schema
from sentry.plugins.base import Notification
from sentry.testutils import TestCase
from sentry.testutils.cases import RuleTestCase
from sentry.testutils.helpers.datetime import before_now, iso_format
from sentry.utils.compat import mock
from sentry.utils.compat.mock import Mock
from sentry.utils.email import MessageBuilder
from sentry.rules.actions.notify_email import (
    NotifyEmailAction,
    NotifyEmailForm,
    MailAdapter,
    NotifyEmailActionTargetType,
)


class NotifyEmailFormTest(TestCase):
    TARGET_TYPE_KEY = "targetType"
    TARGET_IDENTIFIER_KEY = "targetIdentifier"

    def setUp(self):
        super(NotifyEmailFormTest, self).setUp()
        self.user = self.create_user(email="foo@example.com", is_active=True)
        self.user2 = self.create_user(email="baz@example.com", is_active=True)
        self.inactive_user = self.create_user(email="totallynotabot@149.com", is_active=False)

        organization = self.create_organization(owner=self.user)
        self.team = self.create_team(organization=organization)
        self.team_not_in_project = self.create_team(organization=organization)

        self.project = self.create_project(name="Test", teams=[self.team])
        OrganizationMemberTeam.objects.create(
            organizationmember=OrganizationMember.objects.get(
                user=self.user, organization=organization
            ),
            team=self.team,
        )
        self.create_member(user=self.user2, organization=organization, teams=[self.team])
        self.create_member(
            user=self.inactive_user,
            organization=organization,
            teams=[self.team, self.team_not_in_project],
        )

    def form_from_json(self, json):
        return NotifyEmailForm(self.project, json)

    def form_from_values(self, target_type_value, target_id=None):
        json = {self.TARGET_TYPE_KEY: target_type_value}
        if target_id:
            json[self.TARGET_IDENTIFIER_KEY] = target_id
        return self.form_from_json(json)

    def test_validate_empty_fail(self):
        form = self.form_from_json({})
        assert not form.is_valid()

    def test_validate_none_fail(self):
        form = self.form_from_json(None)
        assert not form.is_valid()

    def test_validate_malformed_json_fail(self):
        form = self.form_from_json(
            {"notTheRightK3yName": NotifyEmailActionTargetType.ISSUE_OWNERS.value}
        )
        assert not form.is_valid()

    def test_validate_invalid_target_type_fail(self):
        form = self.form_from_values("TheLegend27")
        assert not form.is_valid()

    def test_validate_issue_owners(self):
        form = self.form_from_values(NotifyEmailActionTargetType.ISSUE_OWNERS.value)
        assert form.is_valid()

    def test_validate_team(self):
        form = self.form_from_values(NotifyEmailActionTargetType.TEAM.value, self.team.id)
        assert form.is_valid()

    def test_validate_team_not_in_project_fail(self):
        form = self.form_from_values(
            NotifyEmailActionTargetType.TEAM.value, self.team_not_in_project.id
        )
        assert not form.is_valid()

    def test_validate_user(self):
        for u in [self.user, self.user2]:
            form = self.form_from_values(NotifyEmailActionTargetType.MEMBER.value, u.id)
            assert form.is_valid()

    def test_validate_inactive_user_fail(self):
        form = self.form_from_values(NotifyEmailActionTargetType.MEMBER.value, self.inactive_user)
        assert not form.is_valid()


class NotifyEmailTest(RuleTestCase):
    rule_cls = NotifyEmailAction

    def test_simple(self):
        event = self.get_event()
        rule = self.get_rule()

        results = list(rule.after(event=event, state=self.get_state()))
        assert len(results) == 1


class MailAdapterTest(TestCase):
    @fixture
    def adapter(self):
        return MailAdapter()

    @mock.patch(
        "sentry.models.ProjectOption.objects.get_value", Mock(side_effect=lambda p, k, d, **kw: d)
    )
    @mock.patch(
        "sentry.rules.actions.notify_email.MailAdapter.get_sendable_users", Mock(return_value=[])
    )
    def test_should_notify_no_sendable_users(self):
        assert not self.adapter.should_notify(group=Mock())

    def test_simple_notification(self):
        event = self.store_event(
            data={"message": "Hello world", "level": "error"}, project_id=self.project.id
        )

        rule = Rule.objects.create(project=self.project, label="my rule")

        notification = Notification(event=event, rule=rule)

        with self.options({"system.url-prefix": "http://example.com"}), self.tasks():
            self.adapter.notify(notification, NotifyEmailActionTargetType.ISSUE_OWNERS.value)

        msg = mail.outbox[0]
        assert msg.subject == "[Sentry] BAR-1 - Hello world"
        assert "my rule" in msg.alternatives[0][0]

    @mock.patch("sentry.interfaces.stacktrace.Stacktrace.get_title")
    @mock.patch("sentry.interfaces.stacktrace.Stacktrace.to_email_html")
    @mock.patch("sentry.rules.actions.notify_email.MailAdapter._send_mail")
    def test_notify_users_renders_interfaces_with_utf8(
        self, _send_mail, _to_email_html, _get_title
    ):
        _to_email_html.return_value = u"רונית מגן"
        _get_title.return_value = "Stacktrace"

        event = self.store_event(
            data={"message": "Soubor ji\xc5\xbe existuje", "stacktrace": {"frames": [{}]}},
            project_id=self.project.id,
        )

        notification = Notification(event=event)

        with self.options({"system.url-prefix": "http://example.com"}):
            self.adapter.notify(notification, NotifyEmailActionTargetType.ISSUE_OWNERS.value)

        _get_title.assert_called_once_with()
        _to_email_html.assert_called_once_with(event)

    @mock.patch("sentry.rules.actions.notify_email.MailAdapter._send_mail")
    def test_notify_users_does_email(self, _send_mail):
        event_manager = EventManager({"message": "hello world", "level": "error"})
        event_manager.normalize()
        event_data = event_manager.get_data()
        event_type = get_event_type(event_data)
        event_data["type"] = event_type.key
        event_data["metadata"] = event_type.get_metadata(event_data)

        event = event_manager.save(self.project.id)
        group = event.group

        notification = Notification(event=event)

        with self.options({"system.url-prefix": "http://example.com"}):
            self.adapter.notify(notification, NotifyEmailActionTargetType.ISSUE_OWNERS.value)

        assert _send_mail.call_count == 1
        args, kwargs = _send_mail.call_args
        self.assertEquals(kwargs.get("project"), self.project)
        self.assertEquals(kwargs.get("reference"), group)
        assert kwargs.get("subject") == u"BAR-1 - hello world"

    @mock.patch("sentry.rules.actions.notify_email.MailAdapter._send_mail")
    def test_multiline_error(self, _send_mail):
        event_manager = EventManager({"message": "hello world\nfoo bar", "level": "error"})
        event_manager.normalize()
        event_data = event_manager.get_data()
        event_type = get_event_type(event_data)
        event_data["type"] = event_type.key
        event_data["metadata"] = event_type.get_metadata(event_data)

        event = event_manager.save(self.project.id)

        notification = Notification(event=event)

        with self.options({"system.url-prefix": "http://example.com"}):
            self.adapter.notify(notification, NotifyEmailActionTargetType.ISSUE_OWNERS.value)

        assert _send_mail.call_count == 1
        args, kwargs = _send_mail.call_args
        assert kwargs.get("subject") == u"BAR-1 - hello world"

    def test_get_sendable_users(self):
        from sentry.models import UserOption, User

        user = self.create_user(email="foo@example.com", is_active=True)
        user2 = self.create_user(email="baz@example.com", is_active=True)
        self.create_user(email="baz2@example.com", is_active=True)

        # user with inactive account
        self.create_user(email="bar@example.com", is_active=False)
        # user not in any groups
        self.create_user(email="bar2@example.com", is_active=True)

        organization = self.create_organization(owner=user)
        team = self.create_team(organization=organization)

        project = self.create_project(name="Test", teams=[team])
        OrganizationMemberTeam.objects.create(
            organizationmember=OrganizationMember.objects.get(user=user, organization=organization),
            team=team,
        )
        self.create_member(user=user2, organization=organization, teams=[team])

        # all members
        assert sorted(set([user.pk, user2.pk])) == sorted(self.adapter.get_sendable_users(project))

        # disabled user2
        UserOption.objects.create(key="mail:alert", value=0, project=project, user=user2)

        assert user2.pk not in self.adapter.get_sendable_users(project)

        user4 = User.objects.create(username="baz4", email="bar@example.com", is_active=True)
        self.create_member(user=user4, organization=organization, teams=[team])
        assert user4.pk in self.adapter.get_sendable_users(project)

        # disabled by default user4
        uo1 = UserOption.objects.create(
            key="subscribe_by_default", value="0", project=project, user=user4
        )

        assert user4.pk not in self.adapter.get_sendable_users(project)

        uo1.delete()

        UserOption.objects.create(
            key="subscribe_by_default", value=u"0", project=project, user=user4
        )

        assert user4.pk not in self.adapter.get_sendable_users(project)

    def test_notify_users_with_utf8_subject(self):
        event = self.store_event(
            data={"message": "רונית מגן", "level": "error"}, project_id=self.project.id
        )

        notification = Notification(event=event)

        with self.options({"system.url-prefix": "http://example.com"}), self.tasks():
            self.adapter.notify(notification, NotifyEmailActionTargetType.ISSUE_OWNERS.value)

        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.subject == u"[Sentry] BAR-1 - רונית מגן"

    def test_get_digest_subject(self):
        assert (
            self.adapter.get_digest_subject(
                mock.Mock(qualified_short_id="BAR-1"),
                {mock.sentinel.group: 3},
                datetime(2016, 9, 19, 1, 2, 3, tzinfo=pytz.utc),
            )
            == "BAR-1 - 1 new alert since Sept. 19, 2016, 1:02 a.m. UTC"
        )

    @mock.patch.object(MailAdapter, "notify", side_effect=MailAdapter.notify, autospec=True)
    def test_notify_digest(self, notify):
        project = self.project
        event = self.store_event(
            data={"timestamp": iso_format(before_now(minutes=1)), "fingerprint": ["group-1"]},
            project_id=project.id,
        )
        event2 = self.store_event(
            data={"timestamp": iso_format(before_now(minutes=1)), "fingerprint": ["group-2"]},
            project_id=project.id,
        )

        rule = project.rule_set.all()[0]
        digest = build_digest(
            project, (event_to_record(event, (rule,)), event_to_record(event2, (rule,)))
        )

        with self.tasks():
            self.adapter.notify_digest(
                project, digest, NotifyEmailActionTargetType.ISSUE_OWNERS.value
            )

        assert notify.call_count == 0
        assert len(mail.outbox) == 1

        message = mail.outbox[0]
        assert "List-ID" in message.message()

    @mock.patch.object(MailAdapter, "notify", side_effect=MailAdapter.notify, autospec=True)
    @mock.patch.object(MessageBuilder, "send_async", autospec=True)
    def test_notify_digest_single_record(self, send_async, notify):
        event = self.store_event(data={}, project_id=self.project.id)
        rule = self.project.rule_set.all()[0]
        digest = build_digest(self.project, (event_to_record(event, (rule,)),))
        self.adapter.notify_digest(
            self.project, digest, NotifyEmailActionTargetType.ISSUE_OWNERS.value
        )
        assert send_async.call_count == 1
        assert notify.call_count == 1

    def test_notify_digest_subject_prefix(self):
        ProjectOption.objects.set_value(
            project=self.project, key=u"mail:subject_prefix", value="[Example prefix] "
        )
        event = self.store_event(
            data={"timestamp": iso_format(before_now(minutes=1)), "fingerprint": ["group-1"]},
            project_id=self.project.id,
        )
        event2 = self.store_event(
            data={"timestamp": iso_format(before_now(minutes=1)), "fingerprint": ["group-2"]},
            project_id=self.project.id,
        )

        rule = self.project.rule_set.all()[0]

        digest = build_digest(
            self.project, (event_to_record(event, (rule,)), event_to_record(event2, (rule,)))
        )

        with self.tasks():
            self.adapter.notify_digest(
                self.project, digest, NotifyEmailActionTargetType.ISSUE_OWNERS.value
            )

        assert len(mail.outbox) == 1

        msg = mail.outbox[0]

        assert msg.subject.startswith("[Example prefix]")

    def test_notify_with_suspect_commits(self):
        repo = Repository.objects.create(
            organization_id=self.organization.id, name=self.organization.id
        )
        release = self.create_release(project=self.project, version="v12")
        release.set_commits(
            [
                {
                    "id": "a" * 40,
                    "repository": repo.name,
                    "author_email": "bob@example.com",
                    "author_name": "Bob",
                    "message": "i fixed a bug",
                    "patch_set": [{"path": "src/sentry/models/release.py", "type": "M"}],
                }
            ]
        )

        event = self.store_event(
            data={
                "message": "Kaboom!",
                "platform": "python",
                "timestamp": iso_format(before_now(seconds=1)),
                "stacktrace": {
                    "frames": [
                        {
                            "function": "handle_set_commits",
                            "abs_path": "/usr/src/sentry/src/sentry/tasks.py",
                            "module": "sentry.tasks",
                            "in_app": True,
                            "lineno": 30,
                            "filename": "sentry/tasks.py",
                        },
                        {
                            "function": "set_commits",
                            "abs_path": "/usr/src/sentry/src/sentry/models/release.py",
                            "module": "sentry.models.release",
                            "in_app": True,
                            "lineno": 39,
                            "filename": "sentry/models/release.py",
                        },
                    ]
                },
                "tags": {"sentry:release": release.version},
            },
            project_id=self.project.id,
        )

        with self.tasks():
            notification = Notification(event=event)

            self.adapter.notify(notification, NotifyEmailActionTargetType.ISSUE_OWNERS.value)

        assert len(mail.outbox) >= 1

        msg = mail.outbox[-1]

        assert "Suspect Commits" in msg.body


class MailAdapterTargetTest(TestCase):
    @fixture
    def adapter(self):
        return MailAdapter()

    def setUp(self):
        from sentry.ownership.grammar import Rule

        self.user = self.create_user(email="foo@625.com", is_active=True)
        self.user2 = self.create_user(email="wilsonler@volleyball.168", is_active=True)
        self.user3 = self.create_user(email="zyn@vikings.com", is_active=True)
        self.user4 = self.create_user(email="vsynk@vikings.com", is_active=True)

        self.organization = self.create_organization(owner=self.user)
        self.team = self.create_team(organization=self.organization)
        self.team2 = self.create_team(organization=self.organization)

        self.project = self.create_project(name="Test", teams=[self.team, self.team2])
        OrganizationMemberTeam.objects.create(
            organizationmember=OrganizationMember.objects.get(
                user=self.user, organization=self.organization
            ),
            team=self.team,
        )
        self.create_member(user=self.user2, organization=self.organization, teams=[self.team])
        self.create_member(user=self.user3, organization=self.organization, teams=[self.team2])
        self.create_member(
            user=self.user4, organization=self.organization, teams=[self.team, self.team2]
        )

        self.group = self.create_group(
            first_seen=timezone.now(),
            last_seen=timezone.now(),
            project=self.project,
            message="hello  world",
            logger="root",
        )
        ProjectOwnership.objects.create(
            project_id=self.project.id,
            schema=dump_schema(
                [
                    Rule(Matcher("path", "*.py"), [Owner("team", self.team.slug)]),
                    Rule(Matcher("path", "*.jx"), [Owner("user", self.user2.email)]),
                    Rule(
                        Matcher("path", "*.cbl"),
                        [Owner("user", self.user.email), Owner("user", self.user2.email)],
                    ),
                ]
            ),
            fallthrough=True,
        )

    def make_event_data(self, filename, url="http://example.com"):
        mgr = EventManager(
            {
                "tags": [("level", "error")],
                "stacktrace": {"frames": [{"lineno": 1, "filename": filename}]},
                "request": {"url": url},
            }
        )
        mgr.normalize()
        data = mgr.get_data()
        event_type = get_event_type(data)
        data["type"] = event_type.key
        data["metadata"] = event_type.get_metadata(data)

        return data

    def assert_notify(self, event, emails_sent_to, target_type, target_identifier=None):
        mail.outbox = []
        with self.options({"system.url-prefix": "http://example.com"}), self.tasks():
            self.adapter.notify(Notification(event=event), target_type, target_identifier)
        assert len(mail.outbox) == len(emails_sent_to)
        assert sorted(email.to[0] for email in mail.outbox) == sorted(emails_sent_to)

    def test_get_send_to_with_team_owners(self):
        event = self.store_event(data=self.make_event_data("foo.py"), project_id=self.project.id)
        assert {self.user.pk, self.user2.pk, self.user4.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.ISSUE_OWNERS.value, event=event.data
        )

        # Make sure that disabling mail alerts works as expected
        UserOption.objects.set_value(
            user=self.user2, key="mail:alert", value=0, project=self.project
        )
        assert {self.user.pk, self.user4.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.ISSUE_OWNERS.value, event=event.data
        )

    def test_get_send_to_with_user_owners(self):
        event = self.store_event(data=self.make_event_data("foo.cbl"), project_id=self.project.id)
        assert {self.user.pk, self.user2.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.ISSUE_OWNERS.value, event=event.data
        )

        # Make sure that disabling mail alerts works as expected
        UserOption.objects.set_value(
            user=self.user2, key="mail:alert", value=0, project=self.project
        )
        assert {self.user.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.ISSUE_OWNERS.value, event=event.data
        )

    def test_get_send_to_with_user_owner(self):
        event = self.store_event(data=self.make_event_data("foo.jx"), project_id=self.project.id)
        assert {self.user2.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.ISSUE_OWNERS.value, event=event.data
        )

    def test_get_send_to_with_fallthrough(self):
        event = self.store_event(data=self.make_event_data("foo.jx"), project_id=self.project.id)
        assert {self.user2.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.ISSUE_OWNERS.value, event=event.data
        )

    def test_get_send_to_without_fallthrough(self):
        ProjectOwnership.objects.get(project_id=self.project.id).update(fallthrough=False)
        event = self.store_event(data=self.make_event_data("foo.cpp"), project_id=self.project.id)
        assert set() == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.ISSUE_OWNERS.value, event=event.data
        )

    def test_notify_users_with_owners(self):
        event_all_users = self.store_event(
            data=self.make_event_data("foo.cbl"), project_id=self.project.id
        )
        self.assert_notify(
            event_all_users,
            [self.user.email, self.user2.email],
            NotifyEmailActionTargetType.ISSUE_OWNERS.value,
        )

        event_team = self.store_event(
            data=self.make_event_data("foo.py"), project_id=self.project.id
        )
        self.assert_notify(
            event_team,
            [self.user.email, self.user2.email, self.user4.email],
            NotifyEmailActionTargetType.ISSUE_OWNERS.value,
        )

        event_single_user = self.store_event(
            data=self.make_event_data("foo.jx"), project_id=self.project.id
        )
        self.assert_notify(
            event_single_user, [self.user2.email], NotifyEmailActionTargetType.ISSUE_OWNERS.value
        )

        # Make sure that disabling mail alerts works as expected
        UserOption.objects.set_value(
            user=self.user2, key="mail:alert", value=0, project=self.project
        )
        event_all_users = self.store_event(
            data=self.make_event_data("foo.cbl"), project_id=self.project.id
        )
        self.assert_notify(
            event_all_users, [self.user.email], NotifyEmailActionTargetType.ISSUE_OWNERS.value
        )

    # TEAMS TESTS
    def test_get_send_to_team(self):
        event = self.store_event(
            data=self.make_event_data("bishan.pay"), project_id=self.project.id
        )

        assert {self.user3.pk, self.user4.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.TEAM.value, self.team2.id, event=event.data
        )

        # Make sure that disabling mail alerts works as expected
        UserOption.objects.set_value(
            user=self.user3, key="mail:alert", value=0, project=self.project
        )
        assert {self.user4.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.TEAM.value, self.team2.id, event=event.data
        )

    def test_notify_users_via_teams(self):
        event = self.store_event(data=self.make_event_data("foo.cbl"), project_id=self.project.id)
        self.assert_notify(
            event,
            [self.user.email, self.user2.email, self.user4.email],
            NotifyEmailActionTargetType.TEAM.value,
            self.team.id,
        )
        self.assert_notify(
            event,
            [self.user3.email, self.user4.email],
            NotifyEmailActionTargetType.TEAM.value,
            self.team2.id,
        )

        # Make sure that disabling mail alerts works as expected
        UserOption.objects.set_value(
            user=self.user2, key="mail:alert", value=0, project=self.project
        )

        self.assert_notify(
            event,
            [self.user.email, self.user4.email],
            NotifyEmailActionTargetType.TEAM.value,
            self.team.id,
        )

    # MEMBERS TESTS
    def test_get_send_to_member(self):
        event = self.store_event(data=self.make_event_data("snoo.py"), project_id=self.project.id)

        assert {self.user3.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.MEMBER.value, self.user3.id, event=event.data
        )

        # Make sure that disabling mail alerts works as expected (User still gets mail)
        UserOption.objects.set_value(
            user=self.user3, key="mail:alert", value=0, project=self.project
        )
        assert {self.user3.pk} == self.adapter.get_send_to(
            self.project, NotifyEmailActionTargetType.MEMBER.value, self.user3.id, event=event.data
        )

    def test_notify_users_via_members(self):
        event = self.store_event(data=self.make_event_data("foo.cbl"), project_id=self.project.id)
        self.assert_notify(
            event, [self.user.email], NotifyEmailActionTargetType.MEMBER.value, self.user.id
        )
        self.assert_notify(
            event, [self.user4.email], NotifyEmailActionTargetType.MEMBER.value, self.user4.id
        )

        # Make sure that disabling mail alerts works as expected (User still gets mail)
        UserOption.objects.set_value(
            user=self.user4, key="mail:alert", value=0, project=self.project
        )

        self.assert_notify(
            event, [self.user4.email], NotifyEmailActionTargetType.MEMBER.value, self.user4.id
        )
