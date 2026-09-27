import { expect, it } from 'vitest';
import JSBI from 'jsbi';
import { bigIntToU8Array, modPow, u8ArrayToBigInt } from './novnc-integers';

it('preserves VNC integers beyond Number precision and padded byte order', () => {
  const bytes = new Uint8Array([
    0, 255, 238, 221, 204, 187, 170, 153, 136, 119,
  ]);
  expect(bigIntToU8Array(u8ArrayToBigInt(bytes), bytes.length)).toEqual(bytes);
  expect(bigIntToU8Array(JSBI.BigInt(0))).toEqual(new Uint8Array([0]));
  expect(bigIntToU8Array(JSBI.BigInt('0x123456'), 1)).toEqual(
    new Uint8Array([0x12, 0x34, 0x56]),
  );
});

it('matches native integer modular exponentiation across large operands', () => {
  const base = 0x123456789abcdef0123456789n;
  const modulus = 0xffffffffffffffffffffffffffc5n;
  for (const exponent of [0n, 1n, 2n, 17n, 257n]) {
    const expected = base ** exponent % modulus;
    const actual = modPow(
      JSBI.BigInt(base.toString()),
      JSBI.BigInt(exponent.toString()),
      JSBI.BigInt(modulus.toString()),
    );
    expect(actual.toString()).toBe(expected.toString());
  }
});
