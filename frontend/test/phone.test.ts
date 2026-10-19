import { expect, test } from 'vitest';
import { normalizePtMobile, ptMobileError } from '../src/utils/phone';

test.each([
  ['912345678', '912345678'],
  ['912 345 678', '912345678'],
  ['+351 912 345 678', '912345678'],
  ['00351912345678', '912345678'],
  ['351-962-345-678', '962345678'],
  ['(93) 1234567', '931234567'],
])('aceita %s', (input, expected) => {
  expect(normalizePtMobile(input)).toBe(expected);
  expect(ptMobileError(input)).toBeNull();
});

test.each([
  ['', 'Indica o número de telemóvel.'],
  ['91234567', 'O número tem de ter 9 algarismos.'],
  ['9123456789', 'O número tem de ter 9 algarismos.'],
  ['212345678', 'Indica um telemóvel português (começa por 91, 92, 93 ou 96).'],
  ['952345678', 'Indica um telemóvel português (começa por 91, 92, 93 ou 96).'],
  ['91234567a', 'O número só pode ter algarismos.'],
])('recusa «%s»', (input, message) => {
  expect(normalizePtMobile(input)).toBeNull();
  expect(ptMobileError(input)).toBe(message);
});
