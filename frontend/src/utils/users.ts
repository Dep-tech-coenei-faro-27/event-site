import { http } from './http';
import type { User } from './authContextValue'; // Usamos a mesma interface

export const getMe = () => http<User>('/users/me');