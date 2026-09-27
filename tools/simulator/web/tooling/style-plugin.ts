import type { RuleTester } from 'oxlint/plugins-dev';

type Rule = Parameters<RuleTester['run']>[1];

const noHashPrivate: Rule = {
  meta: { type: 'suggestion', schema: [] },
  create(context) {
    return {
      PrivateIdentifier(node) {
        context.report({
          node,
          message:
            'Use the TypeScript private modifier instead of a # private member.',
        });
      },
    };
  },
};

export default {
  meta: { name: 'aslice-style' },
  rules: { 'no-hash-private': noHashPrivate },
};
