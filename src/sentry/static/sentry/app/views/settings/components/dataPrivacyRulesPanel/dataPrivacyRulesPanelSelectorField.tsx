import React from 'react';
import styled from '@emotion/styled';

import space from 'app/styles/space';
import {t} from 'app/locale';
import TextField from 'app/components/forms/textField';

const valueTypes = {
  $: [
    'string',
    'number',
    'boolean',
    'datetime',
    'array',
    'object',
    'event',
    'exception',
    'stacktrace',
    'frame',
    'request',
    'user',
    'logentry',
    'thread',
    'breadcrumb',
    'span',
    'sdkv',
  ],
};

const booleanLogicTypes = {
  booleanOperators: ['||', '&&', '!'],
};

const selectorTypes = {
  ...valueTypes,
  ...booleanLogicTypes,
};

type Selector = {
  key: keyof typeof selectorTypes;
  values: Array<string>;
};

type State = {
  showOptions: boolean;
  suggestions: Array<string>;
  selectors: Array<Selector>;
};

type Props = {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  onBlur?: (event: React.KeyboardEvent<HTMLInputElement>) => void;
  disabled?: boolean;
};

class DataPrivacyRulesPanelSelectorField extends React.Component<Props, State> {
  state: State = {
    showOptions: false,
    suggestions: [],
    selectors: [],
  };

  inputField = React.createRef<HTMLInputElement>();

  getCursorPosition = () => {
    if (!this.inputField.current) {
      return -1;
    }
    return this.inputField.current.selectionStart;
  };

  handleChange = (searchTerm: string) => {
    const splittedSearchTerm = searchTerm.split(' ');
    const lastTypedTerm = splittedSearchTerm[splittedSearchTerm.length - 1];

    const {onChange} = this.props;

    if (searchTerm.length === 0) {
      this.setState(
        {
          suggestions: [],
          showOptions: false,
          selectors: [],
        },
        () => {
          onChange(searchTerm);
        }
      );

      return;
    }

    const {selectors} = this.state;

    const currentSelector = selectors[selectors.length - 1];

    if (currentSelector) {
      const afterlastTypedTerm = lastTypedTerm.substr(1);
      const filteredSelectorValues = currentSelector.values.filter(
        selectorValue => selectorValue.indexOf(afterlastTypedTerm.toLowerCase()) > -1
      );

      this.setState(
        {
          suggestions: filteredSelectorValues,
          showOptions: true,
        },
        () => {
          onChange(searchTerm);
        }
      );

      return;
    }

    onChange(searchTerm);
  };

  handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    const {value} = this.props;

    let key = event.key;
    let selectorValues = selectorTypes[event.key];

    if (value.trim().length > 0 && event.which === 32) {
      selectorValues = selectorTypes.booleanOperators;
      key = 'booleanOperators';
    }

    const {selectors} = this.state;
    const currentSelector = selectors[selectors.length - 1];

    if (selectorValues && currentSelector?.key !== key) {
      this.setState({
        selectors: [
          ...selectors,
          {
            key: key as keyof typeof selectorTypes,
            values: selectorValues,
          },
        ],
        suggestions: selectorValues,
        showOptions: true,
      });
    }
  };

  handleClickSuggestionItem = (suggestion: string) => () => {
    const {value, onChange} = this.props;

    this.setState(
      {
        showOptions: false,
      },
      () => {
        onChange(`${value}${suggestion}`);
      }
    );
  };

  render() {
    const {error, onBlur, disabled, value} = this.props;
    const {showOptions, suggestions} = this.state;

    return (
      <Wrapper>
        <StyledTextField
          inputRef={this.inputField}
          name="from"
          placeholder={t('ex. strings, numbers, custom')}
          onChange={this.handleChange}
          autoComplete="off"
          value={value}
          onKeyPress={this.handleKeyPress}
          error={error}
          onBlur={onBlur}
          disabled={disabled}
        />
        {showOptions && suggestions.length > 0 && (
          <Suggestions>
            {suggestions.map(suggestion => (
              <SuggestionItem
                key={suggestion}
                onClick={this.handleClickSuggestionItem(suggestion)}
              >
                {suggestion}
              </SuggestionItem>
            ))}
          </Suggestions>
        )}
      </Wrapper>
    );
  }
}

export default DataPrivacyRulesPanelSelectorField;

const Wrapper = styled('div')`
  position: relative;
  width: 100%;
`;

const StyledTextField = styled(TextField)<{error?: string}>`
  width: 100%;
  height: 40px;
  > * {
    height: 100%;
    min-height: 100%;
  }
  ${p =>
    !p.error &&
    `
      margin-bottom: 0;
    `}
`;

const Suggestions = styled('ul')`
  position: absolute;
  width: 100%;
  padding-left: 0;
  list-style: none;
  margin-bottom: 0;
  box-shadow: 0 2px 0 rgba(37, 11, 54, 0.04);
  border: 1px solid ${p => p.theme.borderDark};
  border-radius: 0 0 ${space(0.5)} ${space(0.5)};
  background: ${p => p.theme.offWhite};
  top: 35px;
  z-index: 1001;
  overflow: hidden;
  max-height: 200px;
  overflow-y: auto;
`;

const SuggestionItem = styled('li')`
  border-bottom: 1px solid ${p => p.theme.borderLight};
  padding: ${space(1)} ${space(2)};
  font-size: ${p => p.theme.fontSizeSmall};
  font-family: ${p => p.theme.text.familyMono};
  cursor: pointer;
  :hover {
    background: ${p => p.theme.offWhite};
  }
`;
