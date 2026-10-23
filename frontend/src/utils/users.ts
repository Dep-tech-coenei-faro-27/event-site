import { http } from './http';
import type { User } from './authContextValue'; // Usamos a mesma interface

export const getMe = (options?: Parameters<typeof http>[1]) => http<User>('/users/me', options);
