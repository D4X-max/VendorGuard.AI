import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../../lib/axios';
import { useAuthStore } from '../../../store/useAuthStore';
import type { LoginRequest, TokenResponse, User } from '../../../types';

export const useLogin = () => {
  const setAuth = useAuthStore((state) => state.setAuth);
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async (credentials: LoginRequest) => {
      // 1. Get the JWT access token
      const { data: tokenData } = await apiClient.post<TokenResponse>(
        '/auth/login',
        credentials
      );

      // 2. Fetch user profile with the fresh token
      const { data: userData } = await apiClient.get<User>('/auth/me', {
        headers: { Authorization: `Bearer ${tokenData.access_token}` },
      });

      return { user: userData, token: tokenData.access_token };
    },
    onSuccess: (data) => {
      // 3. Persist to Zustand + localStorage
      setAuth(data.user, data.token);
      navigate('/');
    },
  });
};