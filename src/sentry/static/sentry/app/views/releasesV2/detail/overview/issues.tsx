import React from 'react';
import styled from '@emotion/styled';

import {t, tct} from 'app/locale';
import DropdownControl, {DropdownItem} from 'app/components/dropdownControl';
import Button from 'app/components/button';
import GroupList from 'app/views/releases/detail/groupList';
import space from 'app/styles/space';
import {Panel, PanelBody} from 'app/components/panels';
import EventView from 'app/views/eventsV2/eventView';
import {formatVersion} from 'app/utils/formatters';
import EmptyStateWarning from 'app/components/emptyStateWarning';
import {DEFAULT_RELATIVE_PERIODS} from 'app/constants';
import withGlobalSelection from 'app/utils/withGlobalSelection';
import {GlobalSelection} from 'app/types';
import Feature from 'app/components/acl/feature';

enum IssuesType {
  NEW = 'new',
  RESOLVED = 'resolved',
  ALL = 'all',
}

type Props = {
  orgId: string;
  version: string;
  selection: GlobalSelection;
  projectId: number;
};

type State = {
  issuesType: IssuesType;
};

class Issues extends React.Component<Props, State> {
  // TODO(releasesV2): we may want to put this in the URL, for now it stays just in state (issues stream is still subject to change)
  state: State = {
    issuesType: IssuesType.NEW,
  };

  getDiscoverUrl() {
    const {version, orgId, projectId} = this.props;

    const discoverQuery = {
      id: undefined,
      version: 2,
      name: `${t('Release')} ${formatVersion(version)}`,
      fields: ['title', 'count()', 'event.type', 'issue', 'last_seen()'],
      query: `release:${version} !event.type:transaction`,
      orderby: '-last_seen',
      projects: [projectId],
    } as const;

    const discoverView = EventView.fromSavedQuery(discoverQuery);
    return discoverView.getResultsViewUrlTarget(orgId);
  }

  getIssuesEndpoint(): {path: string; query: string} {
    const {version, orgId} = this.props;
    const {issuesType} = this.state;

    switch (issuesType) {
      case IssuesType.ALL:
        return {path: `/organizations/${orgId}/issues/`, query: `release:"${version}"`};
      case IssuesType.RESOLVED:
        return {
          path: `/organizations/${orgId}/releases/${version}/resolved/`,
          query: '',
        };
      case IssuesType.NEW:
      default:
        return {
          path: `/organizations/${orgId}/issues/`,
          query: `first-release:"${version}"`,
        };
    }
  }

  handleIssuesTypeSelection = (issuesType: IssuesType) => {
    this.setState({issuesType});
  };

  renderFilterLabel(label: string | undefined) {
    return (
      <React.Fragment>
        <LabelText>{t('Filter')}: &nbsp; </LabelText>
        {label}
      </React.Fragment>
    );
  }

  renderEmptyMessage = () => {
    const {selection} = this.props;
    const {issuesType} = this.state;

    const selectedTimePeriod = DEFAULT_RELATIVE_PERIODS[selection.datetime.period];
    const displayedPeriod = selectedTimePeriod
      ? selectedTimePeriod.toLowerCase()
      : t('given timeframe');

    return (
      <Panel>
        <PanelBody>
          <EmptyStateWarning small withIcon={false}>
            {issuesType === IssuesType.NEW &&
              tct('No new issues in this release for the [timePeriod].', {
                timePeriod: displayedPeriod,
              })}
            {issuesType === IssuesType.RESOLVED &&
              t('No resolved issues in this release.')}
            {issuesType === IssuesType.ALL &&
              tct('No issues in this release for the [timePeriod].', {
                timePeriod: displayedPeriod,
              })}
          </EmptyStateWarning>
        </PanelBody>
      </Panel>
    );
  };

  render() {
    const {issuesType} = this.state;
    const {orgId} = this.props;
    const {path, query} = this.getIssuesEndpoint();
    const issuesTypes = [
      {value: 'new', label: t('New Issues')},
      {value: 'resolved', label: t('Resolved Issues')},
      {value: 'all', label: t('All Issues')},
    ];

    return (
      <React.Fragment>
        <ControlsWrapper>
          <DropdownControl
            label={this.renderFilterLabel(
              issuesTypes.find(i => i.value === issuesType)?.label
            )}
          >
            {issuesTypes.map(({value, label}) => (
              <DropdownItem
                key={value}
                onSelect={this.handleIssuesTypeSelection}
                eventKey={value}
                isActive={value === issuesType}
              >
                {label}
              </DropdownItem>
            ))}
          </DropdownControl>

          <Feature features={['discover-basic']}>
            <Button to={this.getDiscoverUrl()}>{t('Open in Discover')}</Button>
          </Feature>
        </ControlsWrapper>

        <TableWrapper>
          <GroupList
            orgId={orgId}
            endpointPath={path}
            query={query}
            canSelectGroups={false}
            withChart={false}
            renderEmptyMessage={this.renderEmptyMessage}
          />
        </TableWrapper>
      </React.Fragment>
    );
  }
}

const ControlsWrapper = styled('div')`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: ${space(1)};
`;

const TableWrapper = styled('div')`
  margin-bottom: ${space(3)};
  ${Panel} {
    /* smaller space between table and pagination */
    margin-bottom: -${space(1)};
  }
`;

const LabelText = styled('em')`
  font-style: normal;
  color: ${p => p.theme.gray2};
`;

export default withGlobalSelection(Issues);
