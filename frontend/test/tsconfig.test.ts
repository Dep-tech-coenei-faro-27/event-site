/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from 'vitest';

// O `tsc -b` do build só verifica as pastas do `include`. Sem `test/`, os erros de tipos dos testes
// passam despercebidos (o Vitest não verifica tipos).
test('o tsconfig da aplicação verifica também a pasta test/', () => {
  const raw = readFileSync(join(import.meta.dirname, '..', 'tsconfig.app.json'), 'utf8');
  const include = raw.match(/"include"\s*:\s*\[([^\]]*)\]/)?.[1] ?? '';
  const folders = [...include.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  expect(folders).toEqual(expect.arrayContaining(['src', 'test']));
});
