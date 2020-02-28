import React from 'react';

type Props = {
  // Link URL
  href: string;
  // Link content (accepted via string or components / DOM nodes)
  children?: React.ReactNode;
  // Styles applied to the component's root
  className?: string;
  // Action to perform when clicked (will cause the component to be rendered as a button instead of an anchor)
  onClick?: (event: React.MouseEvent<HTMLAnchorElement>) => void;
};

const ExternalLink = React.forwardRef<HTMLAnchorElement, Props>((props, ref) => (
  <a ref={ref} target="_blank" rel="noreferrer noopener" {...props} />
));

export default ExternalLink;
