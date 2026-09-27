import JSBI from 'jsbi';

// noVNC's bigint module uses native integer syntax unavailable in Safari 9.
// Keep its byte conversion and modular arithmetic contract using exact integers.
export function modPow(base: JSBI, exponent: JSBI, modulus: JSBI): JSBI {
  const zero = JSBI.BigInt(0);
  const one = JSBI.BigInt(1);
  let result = one;
  base = JSBI.remainder(base, modulus);
  while (JSBI.greaterThan(exponent, zero)) {
    if (JSBI.equal(JSBI.bitwiseAnd(exponent, one), one)) {
      result = JSBI.remainder(JSBI.multiply(result, base), modulus);
    }
    exponent = JSBI.signedRightShift(exponent, one);
    base = JSBI.remainder(JSBI.multiply(base, base), modulus);
  }
  return result;
}

export function bigIntToU8Array(value: JSBI, padLength = 0): Uint8Array {
  let hex = value.toString(16);
  const length = Math.max(padLength, Math.ceil(hex.length / 2));
  hex = hex.padStart(length * 2, '0');
  const bytes = new Uint8Array(length);
  for (let index = 0; index < length; index += 1) {
    bytes[index] = parseInt(hex.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes;
}

export function u8ArrayToBigInt(bytes: Uint8Array): JSBI {
  const hex = Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
  return JSBI.BigInt(`0x${hex || '0'}`);
}
