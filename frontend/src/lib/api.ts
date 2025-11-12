import axios from "axios";
import { getAuthStore } from "../store/auth";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1",
});

api.interceptors.request.use((config) => {
  const auth = getAuthStore();
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`;
  }
  config.headers["X-Client-Version"] = import.meta.env.VITE_APP_VERSION ?? "dev";
  config.headers["Content-Language"] = "vi-VN";
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const auth = getAuthStore();
    if (error.response?.data?.detail === "token_expired" && auth.refreshToken) {
      try {
        const refreshRes = await api.post("/auth/token/refresh", {
          refresh_token: auth.refreshToken,
        });
        auth.setTokens(refreshRes.data.access_token, refreshRes.data.refresh_token);
        error.config.headers.Authorization = `Bearer ${refreshRes.data.access_token}`;
        return api.request(error.config);
      } catch (refreshError) {
        auth.logout();
      }
    }
    return Promise.reject(error);
  },
);

export default api;
