import React from 'react';
import PropTypes from 'prop-types';

type AnchorProps = React.HTMLProps<HTMLAnchorElement>;

type Props = {
  className?: string;
  openInNewTab?: boolean;
} & Omit<AnchorProps, 'target'>;

const ExternalLink = React.forwardRef<HTMLAnchorElement, Props>(function ExternalLink(
  {openInNewTab = true, ...props},
  ref
) {
  return (
    <a
      ref={ref}
      target={openInNewTab ? '_blank' : '_self'}
      rel="noreferrer noopener"
      {...props}
    />
  );
});

ExternalLink.propTypes = {
  openInNewTab: PropTypes.bool,
};

export default ExternalLink;
