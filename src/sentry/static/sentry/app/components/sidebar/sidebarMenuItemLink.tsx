import React from 'react';

import Link from 'app/components/links/link';
import ExternalLink from 'app/components/links/externalLink';

type Props = {
  // SidebarMenuItemLink content (accepted via string or components / DOM nodes)
  children: React.ReactNode;
  /**
   * Use this prop if button is a react-router link
   */
  to?: string;
  /**
   * specifies whether to open the linked document in a new tab
   */
  openInNewTab?: boolean;
  /**
   * It is raised when the user clicks on the element - optional
   */
  onClick?: () => void;
  /**
   * Inline styles
   */
  style?: React.CSSProperties;
};

const SidebarMenuItemLink = ({to, openInNewTab, ...props}: Props) => {
  if (to) {
    return openInNewTab ? (
      // target is not passed here, as ExternalLink by default opens the link in a new tab
      <ExternalLink href={to} {...props} />
    ) : (
      <Link to={to} {...props} />
    );
  }

  return <div tabIndex={0} {...props} />;
};

export default SidebarMenuItemLink;
