import styled from '@emotion/styled';
import React from 'react';
import omit from 'lodash/omit';

import Link from 'app/components/links/link';
import ExternalLink from 'app/components/links/externalLink';
import InlineSvg from 'app/components/inlineSvg';
import space from 'app/styles/space';

type Size = 'small' | 'normal';
type Priority = 'info' | 'warning' | 'success' | 'error' | 'muted';

type OtherProps = {
  icon?: string;
  onClick?: (e: React.MouseEvent) => void;
};

type DefaultProps = {
  size: Size;
  priority: Priority;
  withoutMarginBottom: boolean;
  openInNewTab: boolean;
  href?: string;
};

type Props = OtherProps & DefaultProps & Partial<Pick<Link['props'], 'to'>>;

type StyledLinkProps = DefaultProps &
  Partial<Pick<Link['props'], 'to'>> &
  Omit<Link['props'], 'to' | 'size'>;

class AlertLink extends React.Component<Props> {
  static defaultProps: DefaultProps = {
    priority: 'warning',
    size: 'normal',
    withoutMarginBottom: false,
    openInNewTab: false,
  };

  render() {
    const {
      size,
      priority,
      icon,
      children,
      onClick,
      withoutMarginBottom,
      openInNewTab,
      to,
      href,
    } = this.props;
    return (
      <StyledLink
        to={to}
        href={href}
        onClick={onClick}
        size={size}
        priority={priority}
        withoutMarginBottom={withoutMarginBottom}
        openInNewTab={openInNewTab}
      >
        {icon && <StyledInlineSvg src={icon} size="1.5em" spacingSize={size} />}
        <AlertLinkText>{children}</AlertLinkText>
        <InlineSvg src="icon-chevron-right" size="1em" />
      </StyledLink>
    );
  }
}

export default AlertLink;

const StyledLink = styled(({openInNewTab, to, href, ref, ...props}: StyledLinkProps) => {
  const linkProps = omit(props, ['withoutMarginBottom', 'priority', 'size']);
  if (href) {
    return (
      <ExternalLink
        {...linkProps}
        href={href}
        ref={ref as React.RefObject<HTMLAnchorElement>}
        openInNewTab={openInNewTab}
      />
    );
  }

  return <Link {...linkProps} ref={ref as any} to={to || '#'} />;
})`
  display: flex;
  align-items: center;
  background-color: ${p => p.theme.alert[p.priority].backgroundLight};
  color: ${p => p.theme.gray4};
  border: 1px dashed ${p => p.theme.alert[p.priority].border};
  padding: ${p => (p.size === 'small' ? `${space(1)} ${space(1.5)}` : space(2))};
  margin-bottom: ${p => (p.withoutMarginBottom ? 0 : space(3))};
  border-radius: 0.25em;
  transition: 0.2s border-color;

  &:hover {
    border-color: ${p => p.theme.blueLight};
  }

  &.focus-visible {
    outline: none;
    box-shadow: ${p => p.theme.alert[p.priority].border}7f 0 0 0 2px;
  }
`;

const AlertLinkText = styled('div')`
  flex-grow: 1;
`;

const StyledInlineSvg = styled(InlineSvg)<{spacingSize: Size}>`
  margin-right: ${p => (p.spacingSize === 'small' ? space(1) : space(1.5))};
`;
