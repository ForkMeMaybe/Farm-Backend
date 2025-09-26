# FarmSense React API Integration Guide

## Table of Contents

1. [Setup & Configuration](#setup--configuration)
2. [Authentication System](#authentication-system)
3. [API Client Configuration](#api-client-configuration)
4. [CRUD Operations](#crud-operations)
5. [Error Handling](#error-handling)
6. [State Management](#state-management)
7. [Real-world Examples](#real-world-examples)
8. [Best Practices](#best-practices)
9. [Testing](#testing)
10. [Performance Optimization](#performance-optimization)

---

## Setup & Configuration

### Prerequisites

```bash
npm install axios react-query @tanstack/react-query
# or
yarn add axios react-query @tanstack/react-query
```

### Environment Configuration

Create `.env` file in your React project root:

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_API_TIMEOUT=10000
REACT_APP_GEMINI_AI_ENABLED=true
```

---

## Authentication System

### JWT Token Management

The backend uses **rest_framework_simplejwt** with **"JWT"** prefix (not "Bearer").

#### Token Storage Utility

```typescript
// utils/tokenStorage.ts
class TokenStorage {
  private static ACCESS_TOKEN_KEY = 'access_token';
  private static REFRESH_TOKEN_KEY = 'refresh_token';
  private static USER_KEY = 'user_data';

  static setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
  }

  static getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY);
  }

  static getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  static clearTokens(): void {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }

  static setUser(user: any): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }

  static getUser(): any {
    const userData = localStorage.getItem(this.USER_KEY);
    return userData ? JSON.parse(userData) : null;
  }

  static isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
}

export default TokenStorage;
```

#### Authentication Service

```typescript
// services/authService.ts
import apiClient from './apiClient';
import TokenStorage from '../utils/tokenStorage';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  re_password: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  owned_farm?: number;
  labourer_profile?: number;
}

class AuthService {
  async login(credentials: LoginCredentials): Promise<{
    access: string;
    refresh: string;
    user: User;
  }> {
    try {
      const response = await apiClient.post('/auth/jwt/create/', credentials);
      const { access, refresh } = response.data;
      
      // Store tokens
      TokenStorage.setTokens(access, refresh);
      
      // Fetch user data
      const userResponse = await apiClient.get('/auth/users/me/');
      const user = userResponse.data;
      TokenStorage.setUser(user);
      
      return { access, refresh, user };
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  }

  async register(data: RegisterData): Promise<User> {
    try {
      const response = await apiClient.post('/auth/users/', data);
      return response.data;
    } catch (error: any) {
      const errors = error.response?.data;
      if (errors) {
        const errorMessages = Object.values(errors).flat().join(', ');
        throw new Error(errorMessages);
      }
      throw new Error('Registration failed');
    }
  }

  async refreshTokens(): Promise<string> {
    const refreshToken = TokenStorage.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await apiClient.post('/auth/jwt/refresh/', {
        refresh: refreshToken,
      });
      
      const { access } = response.data;
      TokenStorage.setTokens(access, refreshToken);
      return access;
    } catch (error) {
      TokenStorage.clearTokens();
      throw new Error('Token refresh failed');
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get('/auth/users/me/');
    const user = response.data;
    TokenStorage.setUser(user);
    return user;
  }

  logout(): void {
    TokenStorage.clearTokens();
    window.location.href = '/login';
  }

  isAuthenticated(): boolean {
    return TokenStorage.isAuthenticated();
  }

  getCurrentUserData(): User | null {
    return TokenStorage.getUser();
  }
}

export default new AuthService();
```

---

## API Client Configuration

### Main API Client

```typescript
// services/apiClient.ts
import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import TokenStorage from '../utils/tokenStorage';

class ApiClient {
  private instance: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: any) => void;
  }> = [];

  constructor() {
    this.instance = axios.create({
      baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
      timeout: parseInt(process.env.REACT_APP_API_TIMEOUT || '10000'),
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor to add auth token
    this.instance.interceptors.request.use(
      (config) => {
        const token = TokenStorage.getAccessToken();
        if (token) {
          config.headers.Authorization = `JWT ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for token refresh
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then((token) => {
              originalRequest.headers.Authorization = `JWT ${token}`;
              return this.instance(originalRequest);
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const refreshToken = TokenStorage.getRefreshToken();
            if (!refreshToken) {
              throw new Error('No refresh token');
            }

            const response = await axios.post(
              `${process.env.REACT_APP_API_BASE_URL}/auth/jwt/refresh/`,
              { refresh: refreshToken }
            );

            const { access } = response.data;
            TokenStorage.setTokens(access, refreshToken);

            // Process failed queue
            this.failedQueue.forEach(({ resolve }) => resolve(access));
            this.failedQueue = [];

            originalRequest.headers.Authorization = `JWT ${access}`;
            return this.instance(originalRequest);
          } catch (refreshError) {
            this.failedQueue.forEach(({ reject }) => reject(refreshError));
            this.failedQueue = [];
            TokenStorage.clearTokens();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // HTTP Methods
  get<T = any>(url: string, params?: any): Promise<AxiosResponse<T>> {
    return this.instance.get(url, { params });
  }

  post<T = any>(url: string, data?: any): Promise<AxiosResponse<T>> {
    return this.instance.post(url, data);
  }

  put<T = any>(url: string, data?: any): Promise<AxiosResponse<T>> {
    return this.instance.put(url, data);
  }

  patch<T = any>(url: string, data?: any): Promise<AxiosResponse<T>> {
    return this.instance.patch(url, data);
  }

  delete<T = any>(url: string): Promise<AxiosResponse<T>> {
    return this.instance.delete(url);
  }
}

export default new ApiClient();
```

---

## CRUD Operations

### Generic API Service

```typescript
// services/baseApiService.ts
import apiClient from './apiClient';
import { AxiosResponse } from 'axios';

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export class BaseApiService<T> {
  constructor(private endpoint: string) {}

  async getAll(params?: any): Promise<T[]> {
    const response: AxiosResponse<T[]> = await apiClient.get(this.endpoint, params);
    return response.data;
  }

  async getAllPaginated(params?: any): Promise<PaginatedResponse<T>> {
    const response: AxiosResponse<PaginatedResponse<T>> = await apiClient.get(
      this.endpoint,
      params
    );
    return response.data;
  }

  async getById(id: number): Promise<T> {
    const response: AxiosResponse<T> = await apiClient.get(`${this.endpoint}${id}/`);
    return response.data;
  }

  async create(data: Partial<T>): Promise<T> {
    const response: AxiosResponse<T> = await apiClient.post(this.endpoint, data);
    return response.data;
  }

  async update(id: number, data: Partial<T>): Promise<T> {
    const response: AxiosResponse<T> = await apiClient.put(
      `${this.endpoint}${id}/`,
      data
    );
    return response.data;
  }

  async partialUpdate(id: number, data: Partial<T>): Promise<T> {
    const response: AxiosResponse<T> = await apiClient.patch(
      `${this.endpoint}${id}/`,
      data
    );
    return response.data;
  }

  async delete(id: number): Promise<void> {
    await apiClient.delete(`${this.endpoint}${id}/`);
  }
}
```

### Specific Service Implementations

#### Farm Service

```typescript
// services/farmService.ts
import { BaseApiService } from './baseApiService';
import apiClient from './apiClient';

export interface Farm {
  id: number;
  owner: number;
  name: string;
  location?: string;
}

class FarmService extends BaseApiService<Farm> {
  constructor() {
    super('/api/farms/');
  }

  // Farm owners can create their farm automatically
  async createMyFarm(data: { name: string; location?: string }): Promise<Farm> {
    return this.create(data);
  }

  // Get current user's farm
  async getMyFarm(): Promise<Farm | null> {
    try {
      const farms = await this.getAll();
      return farms[0] || null; // User should have only one farm
    } catch (error) {
      return null;
    }
  }
}

export default new FarmService();
```

#### Livestock Service

```typescript
// services/livestockService.ts
import { BaseApiService } from './baseApiService';
import apiClient from './apiClient';

export interface Livestock {
  id: number;
  farm: number;
  tag_id: string;
  species: string;
  breed: string;
  date_of_birth: string;
  gender: 'M' | 'F';
  health_status: 'healthy' | 'sick' | 'recovering';
  current_weight_kg?: number;
}

class LivestockService extends BaseApiService<Livestock> {
  constructor() {
    super('/api/livestock/');
  }

  async getByFarm(farmId: number): Promise<Livestock[]> {
    return this.getAll({ farm: farmId });
  }

  async getBySpecies(species: string): Promise<Livestock[]> {
    return this.getAll({ species });
  }

  async getByHealthStatus(status: string): Promise<Livestock[]> {
    return this.getAll({ health_status: status });
  }

  async searchByTagId(tagId: string): Promise<Livestock[]> {
    return this.getAll({ search: tagId });
  }
}

export default new LivestockService();
```

#### Health Record Service

```typescript
// services/healthRecordService.ts
import { BaseApiService } from './baseApiService';
import apiClient from './apiClient';

export interface AMURecord {
  id: number;
  health_record: number;
  drug?: number;
  drug_name?: string;
  dosage: string;
  withdrawal_period: number;
}

export interface HealthRecord {
  id: number;
  livestock: number;
  event_type: 'vaccination' | 'sickness' | 'check-up' | 'treatment';
  event_date: string;
  notes?: string;
  diagnosis?: string;
  treatment_outcome?: string;
  amu_records: AMURecord[];
}

class HealthRecordService extends BaseApiService<HealthRecord> {
  constructor() {
    super('/api/health-records/');
  }

  async getByLivestock(livestockId: number): Promise<HealthRecord[]> {
    return this.getAll({ livestock: livestockId });
  }

  async getByEventType(eventType: string): Promise<HealthRecord[]> {
    return this.getAll({ event_type: eventType });
  }

  async getRecent(limit: number = 10): Promise<HealthRecord[]> {
    const response = await apiClient.get(this.endpoint, {
      ordering: '-event_date',
      limit,
    });
    return response.data.results || response.data;
  }
}

export default new HealthRecordService();
```

#### AMU Service with AI Integration

```typescript
// services/amuService.ts
import { BaseApiService } from './baseApiService';
import apiClient from './apiClient';

export interface AMURecord {
  id: number;
  health_record: number;
  drug?: number;
  drug_name?: string;
  dosage: string;
  withdrawal_period: number;
}

export interface AMUInsightResponse {
  insights: string;
}

export interface AMUChartData {
  chart_data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      backgroundColor: string;
      borderColor: string;
      borderWidth: number;
      fill: boolean;
    }>;
  };
  summary: {
    total_treatments: number;
    unique_drugs: number;
    time_period: string;
  };
}

class AMUService extends BaseApiService<AMURecord> {
  constructor() {
    super('/api/amu-records/');
  }

  async getByHealthRecord(healthRecordId: number): Promise<AMURecord[]> {
    return this.getAll({ health_record: healthRecordId });
  }

  async getByLivestock(livestockId: number): Promise<AMURecord[]> {
    return this.getAll({ health_record__livestock: livestockId });
  }

  // AI-powered insights using Gemini
  async generateInsights(livestockId: number): Promise<AMUInsightResponse> {
    const response = await apiClient.post('/api/amu-insights/generate/', {
      livestock_id: livestockId,
    });
    return response.data;
  }

  // Get chart data for analytics
  async getChartData(livestockId: number): Promise<AMUChartData> {
    const response = await apiClient.get('/api/amu-insights/chart-data/', {
      livestock_id: livestockId,
    });
    return response.data;
  }
}

export default new AMUService();
```

#### Labourer Service

```typescript
// services/labourerService.ts
import { BaseApiService } from './baseApiService';
import apiClient from './apiClient';

export interface Labourer {
  id: number;
  user: number;
  farm?: number;
  status: 'pending' | 'approved' | 'rejected';
  user_name: string;
  user_email: string;
  farm_name?: string;
}

class LabourerService extends BaseApiService<Labourer> {
  constructor() {
    super('/api/labourers/');
  }

  // Create labourer profile (for current user)
  async createProfile(): Promise<Labourer> {
    return this.create({});
  }

  // Request to join a farm
  async joinFarm(labourerId: number, farmId: number): Promise<{ detail: string }> {
    const response = await apiClient.post(
      `/api/labourers/${labourerId}/join_farm/`,
      { farm_id: farmId }
    );
    return response.data;
  }

  // Approve labourer (farm owner only)
  async approve(labourerId: number): Promise<{ detail: string }> {
    const response = await apiClient.post(`/api/labourers/${labourerId}/approve/`);
    return response.data;
  }

  // Reject labourer (farm owner only)
  async reject(labourerId: number): Promise<{ detail: string }> {
    const response = await apiClient.post(`/api/labourers/${labourerId}/reject/`);
    return response.data;
  }

  // Get pending requests for farm owner
  async getPendingRequests(): Promise<Labourer[]> {
    return this.getAll({ status: 'pending' });
  }

  // Get approved labourers
  async getApprovedLabourers(): Promise<Labourer[]> {
    return this.getAll({ status: 'approved' });
  }
}

export default new LabourerService();
```

---

## Error Handling

### Global Error Handler

```typescript
// utils/errorHandler.ts
import { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  status?: number;
  field?: string;
  details?: any;
}

export class ErrorHandler {
  static handleApiError(error: AxiosError): ApiError {
    if (!error.response) {
      return {
        message: 'Network error. Please check your connection.',
        status: 500,
      };
    }

    const { status, data } = error.response;
    let message = 'An unexpected error occurred.';
    let field = '';

    switch (status) {
      case 400:
        if (typeof data === 'object' && data !== null) {
          // Handle validation errors
          const errorMessages = Object.entries(data).map(([key, value]) => {
            field = key;
            return Array.isArray(value) ? value.join(', ') : String(value);
          });
          message = errorMessages.join('. ');
        } else {
          message = 'Invalid request data.';
        }
        break;

      case 401:
        message = 'Authentication required. Please login.';
        break;

      case 403:
        message = 'You do not have permission to perform this action.';
        break;

      case 404:
        message = 'The requested resource was not found.';
        break;

      case 429:
        message = 'Too many requests. Please try again later.';
        break;

      case 500:
        message = 'Server error. Please try again later.';
        break;

      default:
        message = (data as any)?.detail || `Error ${status}: Something went wrong.`;
    }

    return {
      message,
      status,
      field,
      details: data,
    };
  }

  static showError(error: any, showToast?: (message: string) => void): void {
    const apiError = this.handleApiError(error);
    
    if (showToast) {
      showToast(apiError.message);
    } else {
      console.error('API Error:', apiError);
    }
  }
}
```

### Error Boundary Component

```typescript
// components/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error Boundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong.</h2>
          <details style={{ whiteSpace: 'pre-wrap' }}>
            {this.state.error && this.state.error.toString()}
          </details>
          <button onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

---

## State Management

### React Query Integration

```typescript
// hooks/useAuth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import authService, { LoginCredentials, RegisterData, User } from '../services/authService';
import { ErrorHandler } from '../utils/errorHandler';

export const useAuth = () => {
  const queryClient = useQueryClient();

  const login = useMutation({
    mutationFn: (credentials: LoginCredentials) => authService.login(credentials),
    onSuccess: (data) => {
      queryClient.setQueryData(['user'], data.user);
    },
    onError: (error) => {
      ErrorHandler.showError(error);
    },
  });

  const register = useMutation({
    mutationFn: (data: RegisterData) => authService.register(data),
    onError: (error) => {
      ErrorHandler.showError(error);
    },
  });

  const user = useQuery({
    queryKey: ['user'],
    queryFn: authService.getCurrentUser,
    enabled: authService.isAuthenticated(),
    retry: false,
  });

  const logout = () => {
    authService.logout();
    queryClient.clear();
  };

  return {
    login,
    register,
    logout,
    user: user.data,
    isLoading: user.isLoading || login.isPending || register.isPending,
    isAuthenticated: authService.isAuthenticated(),
  };
};
```

### Custom Hooks for API Operations

```typescript
// hooks/useLivestock.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import livestockService, { Livestock } from '../services/livestockService';
import { ErrorHandler } from '../utils/errorHandler';

export const useLivestock = () => {
  const queryClient = useQueryClient();

  const livestock = useQuery({
    queryKey: ['livestock'],
    queryFn: livestockService.getAll,
  });

  const createLivestock = useMutation({
    mutationFn: (data: Partial<Livestock>) => livestockService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['livestock'] });
    },
    onError: ErrorHandler.showError,
  });

  const updateLivestock = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Livestock> }) =>
      livestockService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['livestock'] });
    },
    onError: ErrorHandler.showError,
  });

  const deleteLivestock = useMutation({
    mutationFn: (id: number) => livestockService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['livestock'] });
    },
    onError: ErrorHandler.showError,
  });

  return {
    livestock: livestock.data || [],
    isLoading: livestock.isLoading,
    createLivestock,
    updateLivestock,
    deleteLivestock,
    refetch: livestock.refetch,
  };
};

// Hook for specific livestock
export const useLivestockById = (id: number) => {
  return useQuery({
    queryKey: ['livestock', id],
    queryFn: () => livestockService.getById(id),
    enabled: !!id,
  });
};
```

```typescript
// hooks/useAMU.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import amuService, { AMURecord } from '../services/amuService';
import { ErrorHandler } from '../utils/errorHandler';

export const useAMU = () => {
  const queryClient = useQueryClient();

  const amuRecords = useQuery({
    queryKey: ['amu-records'],
    queryFn: amuService.getAll,
  });

  const generateInsights = useMutation({
    mutationFn: (livestockId: number) => amuService.generateInsights(livestockId),
    onError: ErrorHandler.showError,
  });

  const chartData = useMutation({
    mutationFn: (livestockId: number) => amuService.getChartData(livestockId),
    onError: ErrorHandler.showError,
  });

  return {
    amuRecords: amuRecords.data || [],
    isLoading: amuRecords.isLoading,
    generateInsights,
    chartData,
    refetch: amuRecords.refetch,
  };
};

export const useAMUByLivestock = (livestockId: number) => {
  return useQuery({
    queryKey: ['amu-records', 'livestock', livestockId],
    queryFn: () => amuService.getByLivestock(livestockId),
    enabled: !!livestockId,
  });
};
```

---

## Real-world Examples

### Login Component

```typescript
// components/LoginForm.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const LoginForm: React.FC = () => {
  const navigate = useNavigate();
  const { login, isLoading } = useAuth();
  const [credentials, setCredentials] = useState({
    email: '',
    password: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await login.mutateAsync(credentials);
      navigate('/dashboard');
    } catch (error) {
      // Error handling is done in the mutation
    }
  };

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <h2>Login to FarmSense</h2>
      
      <div className="form-group">
        <label htmlFor="email">Email:</label>
        <input
          type="email"
          id="email"
          value={credentials.email}
          onChange={(e) => setCredentials({ ...credentials, email: e.target.value })}
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="password">Password:</label>
        <input
          type="password"
          id="password"
          value={credentials.password}
          onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
          required
        />
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary">
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
};

export default LoginForm;
```

### Livestock Management Component

```typescript
// components/LivestockList.tsx
import React, { useState } from 'react';
import { useLivestock } from '../hooks/useLivestock';
import { Livestock } from '../services/livestockService';

const LivestockList: React.FC = () => {
  const { livestock, isLoading, deleteLivestock } = useLivestock();
  const [filter, setFilter] = useState('');

  const filteredLivestock = livestock.filter(animal =>
    animal.tag_id.toLowerCase().includes(filter.toLowerCase()) ||
    animal.species.toLowerCase().includes(filter.toLowerCase())
  );

  const handleDelete = async (id: number, tagId: string) => {
    if (window.confirm(`Are you sure you want to delete ${tagId}?`)) {
      await deleteLivestock.mutateAsync(id);
    }
  };

  if (isLoading) {
    return <div className="loading">Loading livestock...</div>;
  }

  return (
    <div className="livestock-list">
      <h2>Livestock Management</h2>
      
      <div className="controls">
        <input
          type="text"
          placeholder="Search by tag ID or species..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="livestock-grid">
        {filteredLivestock.map(animal => (
          <div key={animal.id} className="livestock-card">
            <div className="card-header">
              <h3>{animal.tag_id}</h3>
              <span className={`status ${animal.health_status}`}>
                {animal.health_status}
              </span>
            </div>
            
            <div className="card-body">
              <p><strong>Species:</strong> {animal.species}</p>
              <p><strong>Breed:</strong> {animal.breed}</p>
              <p><strong>Gender:</strong> {animal.gender === 'M' ? 'Male' : 'Female'}</p>
              <p><strong>Birth Date:</strong> {animal.date_of_birth}</p>
              {animal.current_weight_kg && (
                <p><strong>Weight:</strong> {animal.current_weight_kg} kg</p>
              )}
            </div>

            <div className="card-actions">
              <button 
                onClick={() => handleDelete(animal.id, animal.tag_id)}
                className="btn-danger"
                disabled={deleteLivestock.isPending}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LivestockList;
```

### AMU Insights Dashboard

```typescript
// components/AMUInsights.tsx
import React, { useState } from 'react';
import { useAMU } from '../hooks/useAMU';
import { useLivestock } from '../hooks/useLivestock';
import { Chart } from 'react-chartjs-2';

const AMUInsights: React.FC = () => {
  const { livestock } = useLivestock();
  const { generateInsights, chartData } = useAMU();
  const [selectedLivestock, setSelectedLivestock] = useState<number | null>(null);
  const [insights, setInsights] = useState<string>('');
  const [chart, setChart] = useState<any>(null);

  const handleGenerateInsights = async () => {
    if (!selectedLivestock) return;

    try {
      const result = await generateInsights.mutateAsync(selectedLivestock);
      setInsights(result.insights);
    } catch (error) {
      console.error('Failed to generate insights:', error);
    }
  };

  const handleGetChartData = async () => {
    if (!selectedLivestock) return;

    try {
      const result = await chartData.mutateAsync(selectedLivestock);
      setChart(result);
    } catch (error) {
      console.error('Failed to get chart data:', error);
    }
  };

  return (
    <div className="amu-insights">
      <h2>AMU Insights Dashboard</h2>

      <div className="controls">
        <select
          value={selectedLivestock || ''}
          onChange={(e) => setSelectedLivestock(Number(e.target.value) || null)}
        >
          <option value="">Select Livestock</option>
          {livestock.map(animal => (
            <option key={animal.id} value={animal.id}>
              {animal.tag_id} - {animal.species}
            </option>
          ))}
        </select>

        <button
          onClick={handleGenerateInsights}
          disabled={!selectedLivestock || generateInsights.isPending}
          className="btn-primary"
        >
          {generateInsights.isPending ? 'Generating...' : 'Generate AI Insights'}
        </button>

        <button
          onClick={handleGetChartData}
          disabled={!selectedLivestock || chartData.isPending}
          className="btn-secondary"
        >
          {chartData.isPending ? 'Loading...' : 'Get Chart Data'}
        </button>
      </div>

      {insights && (
        <div className="insights-section">
          <h3>AI-Generated Insights</h3>
          <div className="insights-content">
            {insights.split('\n').map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
        </div>
      )}

      {chart && (
        <div className="chart-section">
          <h3>AMU Usage Trends</h3>
          <div className="chart-container">
            <Chart
              type="line"
              data={chart.chart_data}
              options={{
                responsive: true,
                plugins: {
                  title: {
                    display: true,
                    text: 'AMU Usage Over Time',
                  },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                  },
                },
              }}
            />
          </div>
          
          <div className="chart-summary">
            <h4>Summary</h4>
            <p>Total Treatments: {chart.summary.total_treatments}</p>
            <p>Unique Drugs: {chart.summary.unique_drugs}</p>
            <p>Time Period: {chart.summary.time_period}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default AMUInsights;
```

---

## Best Practices

### 1. API Response Handling

```typescript
// utils/apiHelpers.ts
export const handleApiResponse = <T>(
  response: Promise<T>,
  onSuccess?: (data: T) => void,
  onError?: (error: any) => void
) => {
  return response
    .then((data) => {
      onSuccess?.(data);
      return data;
    })
    .catch((error) => {
      const handledError = ErrorHandler.handleApiError(error);
      onError?.(handledError);
      throw handledError;
    });
};
```

### 2. Request Cancellation

```typescript
// hooks/useAbortController.ts
import { useEffect, useRef } from 'react';

export const useAbortController = () => {
  const abortControllerRef = useRef<AbortController>();

  useEffect(() => {
    abortControllerRef.current = new AbortController();
    
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const getSignal = () => abortControllerRef.current?.signal;

  return { getSignal };
};
```

### 3. Optimistic Updates

```typescript
// hooks/useOptimisticLivestock.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import livestockService, { Livestock } from '../services/livestockService';

export const useOptimisticLivestock = () => {
  const queryClient = useQueryClient();

  const updateLivestock = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Livestock> }) =>
      livestockService.update(id, data),
    
    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['livestock'] });

      // Snapshot previous value
      const previousLivestock = queryClient.getQueryData(['livestock']);

      // Optimistically update cache
      queryClient.setQueryData(['livestock'], (old: Livestock[] = []) =>
        old.map(animal => animal.id === id ? { ...animal, ...data } : animal)
      );

      return { previousLivestock };
    },

    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousLivestock) {
        queryClient.setQueryData(['livestock'], context.previousLivestock);
      }
    },

    onSettled: () => {
      // Always refresh after mutation
      queryClient.invalidateQueries({ queryKey: ['livestock'] });
    },
  });

  return { updateLivestock };
};
```

### 4. Batch Operations

```typescript
// services/batchOperations.ts
import apiClient from './apiClient';

export class BatchOperations {
  static async batchUpdate<T>(
    endpoint: string,
    updates: Array<{ id: number; data: Partial<T> }>
  ): Promise<T[]> {
    const promises = updates.map(({ id, data }) =>
      apiClient.put(`${endpoint}${id}/`, data)
    );
    
    const responses = await Promise.allSettled(promises);
    
    const results: T[] = [];
    const errors: any[] = [];
    
    responses.forEach((response, index) => {
      if (response.status === 'fulfilled') {
        results.push(response.value.data);
      } else {
        errors.push({
          index,
          id: updates[index].id,
          error: response.reason,
        });
      }
    });
    
    if (errors.length > 0) {
      console.warn('Batch update errors:', errors);
    }
    
    return results;
  }

  static async batchDelete(
    endpoint: string,
    ids: number[]
  ): Promise<{ success: number[]; failed: number[] }> {
    const promises = ids.map(id => 
      apiClient.delete(`${endpoint}${id}/`).then(() => id)
    );
    
    const responses = await Promise.allSettled(promises);
    
    const success: number[] = [];
    const failed: number[] = [];
    
    responses.forEach((response, index) => {
      if (response.status === 'fulfilled') {
        success.push(response.value);
      } else {
        failed.push(ids[index]);
      }
    });
    
    return { success, failed };
  }
}
```

---

## Testing

### API Service Testing

```typescript
// __tests__/services/livestockService.test.ts
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import apiClient from '../../services/apiClient';
import livestockService from '../../services/livestockService';

// Mock the API client
jest.mock('../../services/apiClient');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('LivestockService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch all livestock', async () => {
    const mockData = [
      {
        id: 1,
        tag_id: 'COW001',
        species: 'Cattle',
        breed: 'Holstein',
        gender: 'F',
        health_status: 'healthy',
      },
    ];

    mockedApiClient.get.mockResolvedValue({ data: mockData });

    const result = await livestockService.getAll();

    expect(mockedApiClient.get).toHaveBeenCalledWith('/api/livestock/', undefined);
    expect(result).toEqual(mockData);
  });

  it('should create new livestock', async () => {
    const newLivestock = {
      tag_id: 'COW002',
      species: 'Cattle',
      breed: 'Angus',
      gender: 'M' as const,
      date_of_birth: '2023-01-15',
    };

    const createdLivestock = { id: 2, farm: 1, ...newLivestock };
    mockedApiClient.post.mockResolvedValue({ data: createdLivestock });

    const result = await livestockService.create(newLivestock);

    expect(mockedApiClient.post).toHaveBeenCalledWith('/api/livestock/', newLivestock);
    expect(result).toEqual(createdLivestock);
  });

  it('should handle API errors', async () => {
    const error = {
      response: {
        status: 400,
        data: { tag_id: ['This field is required.'] },
      },
    };

    mockedApiClient.post.mockRejectedValue(error);

    await expect(livestockService.create({})).rejects.toThrow();
  });
});
```

### Hook Testing

```typescript
// __tests__/hooks/useLivestock.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useLivestock } from '../../hooks/useLivestock';
import livestockService from '../../services/livestockService';

// Mock the service
jest.mock('../../services/livestockService');
const mockedLivestockService = livestockService as jest.Mocked<typeof livestockService>;

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useLivestock', () => {
  it('should fetch livestock data', async () => {
    const mockData = [{ id: 1, tag_id: 'COW001', species: 'Cattle' }];
    mockedLivestockService.getAll.mockResolvedValue(mockData);

    const { result } = renderHook(() => useLivestock(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.livestock).toEqual(mockData);
    });
  });
});
```

---

## Performance Optimization

### 1. Pagination Implementation

```typescript
// hooks/usePaginatedLivestock.ts
import { useInfiniteQuery } from '@tanstack/react-query';
import livestockService from '../services/livestockService';

export const usePaginatedLivestock = (pageSize = 20) => {
  return useInfiniteQuery({
    queryKey: ['livestock', 'paginated'],
    queryFn: ({ pageParam = 1 }) =>
      livestockService.getAllPaginated({
        page: pageParam,
        page_size: pageSize,
      }),
    getNextPageParam: (lastPage) => {
      if (lastPage.next) {
        const url = new URL(lastPage.next);
        return url.searchParams.get('page');
      }
      return undefined;
    },
    initialPageParam: 1,
  });
};
```

### 2. Data Prefetching

```typescript
// utils/prefetch.ts
import { QueryClient } from '@tanstack/react-query';
import livestockService from '../services/livestockService';

export const prefetchLivestockData = async (queryClient: QueryClient) => {
  await queryClient.prefetchQuery({
    queryKey: ['livestock'],
    queryFn: livestockService.getAll,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
```

### 3. Background Sync

```typescript
// hooks/useBackgroundSync.ts
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export const useBackgroundSync = () => {
  const queryClient = useQueryClient();

  useEffect(() => {
    const handleFocus = () => {
      queryClient.invalidateQueries();
    };

    const handleOnline = () => {
      queryClient.resumePausedMutations();
    };

    window.addEventListener('focus', handleFocus);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('online', handleOnline);
    };
  }, [queryClient]);
};
```

---

## Conclusion

This comprehensive React API integration guide provides everything needed to build a robust frontend for the FarmSense livestock management system. The implementation includes:

- **Secure JWT authentication** with automatic token refresh
- **Complete CRUD operations** for all entities
- **AI integration** with Gemini for AMU insights
- **Advanced error handling** and user feedback
- **Performance optimization** with React Query
- **Comprehensive testing** strategies
- **Production-ready patterns** and best practices

The guide follows modern React patterns and ensures scalability, maintainability, and excellent user experience while integrating seamlessly with the Django REST API backend.
