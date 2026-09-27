import { sha256 as digest } from 'js-sha256';

let pendingDownload: string | undefined;

export function encode(bytes: Uint8Array): string {
  return btoa(Array.from(bytes, (byte) => String.fromCharCode(byte)).join(''));
}

export function decode(value: string): Uint8Array<ArrayBuffer> {
  return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
}

export function encodeText(value: string): string {
  return encode(new TextEncoder().encode(value));
}

export async function sha256(bytes: Uint8Array<ArrayBuffer>): Promise<string> {
  return digest(bytes);
}

export function download(
  bytes: Uint8Array<ArrayBuffer>,
  filename: string,
): void {
  const url = URL.createObjectURL(new Blob([bytes]));
  const link = document.createElement('a');
  link.href = url;
  if ('download' in HTMLAnchorElement.prototype) {
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return;
  }
  // Safari 9 needs a real user click to open a completed asynchronous export.
  if (pendingDownload) {
    URL.revokeObjectURL(pendingDownload);
  }
  pendingDownload = url;
  const notice = document.getElementById('download-ready');
  link.target = '_blank';
  link.rel = 'noopener';
  link.textContent = `Open ${filename}`;
  notice?.replaceChildren(link, ' — then use File > Save As to save the file.');
  if (notice) {
    notice.hidden = false;
  }
}
