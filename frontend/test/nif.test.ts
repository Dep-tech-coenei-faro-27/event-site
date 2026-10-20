import { expect, test } from 'vitest';
import { isValidNif, nifError } from '../src/utils/nif';

test.each(['123456789', '123 456 789', 'PT123456789', '501964843', '999999990'])(
  'aceita %s',
  (nif) => {
    expect(isValidNif(nif)).toBe(true);
    expect(nifError(nif)).toBeNull();
  },
);

test('vazio é aceite (o campo é opcional)', () => {
  expect(nifError('')).toBeNull();
  expect(nifError('   ')).toBeNull();
});

test.each([
  ['12345678', 'O NIF tem de ter 9 algarismos.'],
  ['1234567890', 'O NIF tem de ter 9 algarismos.'],
  ['12345678a', 'O NIF tem de ter 9 algarismos.'],
  ['123456780', 'Este NIF não é válido. Confirma os algarismos.'],
])('recusa %s', (nif, message) => {
  expect(nifError(nif)).toBe(message);
});
