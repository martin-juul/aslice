// noVNC 1.7 exports its entry point at the package root. The upstream
// community declarations still name the previous lib/rfb entry point.
declare module '@novnc/novnc' {
  export { default } from '@novnc/novnc/lib/rfb';
}
