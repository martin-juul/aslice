import type { Plugin } from 'postcss';

export function cssCompatibility(): Plugin {
  return {
    postcssPlugin: 'console-safari-nine-css',
    Declaration(declaration) {
      // xterm's optional VS Code scrollbar shadow uses a custom-property fallback.
      declaration.value = declaration.value.replace(
        /var\(--vscode-scrollbar-shadow,\s*#000\)/g,
        '#000',
      );
    },
  };
}
