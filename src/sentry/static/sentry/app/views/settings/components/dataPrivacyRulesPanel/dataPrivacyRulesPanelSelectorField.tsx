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

// const booleanLogicTypes = {
//   '|': '|',
//   '&': '&',
//   '!': '!',
// };

const selectors = {
  ...valueTypes,
  //   ...booleanLogicTypes,
};

type State = {
  searchTerm: string;
  showOptions: boolean;
  suggestions: Array<string>;
  selector?: {
    key: keyof typeof selectors;
    values: Array<string>;
  };
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
    searchTerm: '',
    showOptions: false,
    suggestions: [],
  };

  handleChange = (searchTerm: string) => {
    if (searchTerm.length === 0) {
      this.setState({
        searchTerm,
        suggestions: [],
        showOptions: false,
        selector: undefined,
      });

      return;
    }

    const {selector} = this.state;

    if (
      selector?.key &&
      searchTerm !== selector?.key &&
      !selectors[selector?.key].includes(searchTerm.substr(1))
    ) {
      const searchTermAfterSelector = searchTerm.substr(1);
      const filteredSelectorValues = selector.values.filter(
        selectorValue => selectorValue.indexOf(searchTermAfterSelector.toLowerCase()) > -1
      );

      this.setState({
        searchTerm,
        suggestions: filteredSelectorValues,
        showOptions: true,
      });

      return;
    }

    this.setState(
      {
        searchTerm,
      },
      () => {
        //this.props.onChange(this.state.searchTerm);
      }
    );
  };

  handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    const selectorValues = selectors[event.key];

    if (selectorValues && event.key !== this.state.selector?.key) {
      this.setState({
        selector: {
          key: event.key as keyof typeof selectors,
          values: selectorValues,
        },
        suggestions: selectorValues,
        showOptions: true,
      });
    }
  };

  handleClickSuggestionItem = (suggestion: string) => () => {
    this.setState(prevState => ({
      searchTerm: `${prevState.selector?.key}${suggestion}`,
      showOptions: false,
    }));
  };

  render() {
    const {error, onBlur, disabled} = this.props;
    const {searchTerm, showOptions, suggestions} = this.state;

    return (
      <Wrapper>
        <StyledTextField
          name="from"
          placeholder={t('ex. strings, numbers, custom')}
          onChange={this.handleChange}
          autoComplete="off"
          value={searchTerm}
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
