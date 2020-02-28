import React from 'react';
import classNames from 'classnames';

import Button from 'app/components/button';
import Confirm from 'app/components/confirm';

import Link from './link';

type Props = {
  message: React.ReactNode;
  title: string;
  onConfirm: () => void;
  disabled?: boolean;
  className?: string;
  priority?: React.ComponentProps<typeof Button>['priority'];
};

/**
 * <Confirm> is a more generic version of this component
 */
class LinkWithConfirmation extends React.PureComponent<Props> {
  render() {
    const {className, disabled, title, children, ...otherProps} = this.props;
    return (
      <Confirm {...otherProps} disabled={disabled}>
        <Link
          className={classNames(className || '', {disabled})}
          disabled={disabled}
          title={title}
        >
          {children}
        </Link>
      </Confirm>
    );
  }
}

export default LinkWithConfirmation;
