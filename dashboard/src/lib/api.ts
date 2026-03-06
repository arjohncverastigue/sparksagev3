const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FetchOptions extends RequestInit {
  token?: string;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, headers: customHeaders, body, ...rest } = options; // Destructure body here

  const headers: Record<string, string> = {
    ...((customHeaders as Record<string, string>) || {}),
  };

  // Only set Content-Type: application/json if body is not FormData
  if (!(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    headers,
    body: (body instanceof FormData || typeof body === 'string') ? body : JSON.stringify(body), // Only stringify if it's an object
    ...rest,
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    console.error("API Error Response:", errBody);
    // Ensure detail is stringified if it's an object/array, otherwise use directly
    const errorMessage = typeof errBody.detail === 'object' && errBody.detail !== null
      ? JSON.stringify(errBody.detail)
      : errBody.detail;
    throw new Error(errorMessage || `API error: ${res.status}`);
  }

  // Handle 204 No Content responses
  if (res.status === 204) {
    return null as T;
  }

  return res.json();
}

// Response types matching backend
export interface ProviderItem {
  name: string;
  display_name: string;
  model: string;
  free: boolean;
  configured: boolean;
  is_primary: boolean;
}

export interface ProvidersResponse {
  providers: ProviderItem[];
  fallback_order: string[];
}

export interface ChannelItem {
  channel_id: string;
  message_count: number;
  last_active: string;
}

// Channel list returned by new guild-channel API
export interface ChannelInfo {
  id: string;
  name: string;
}

export interface ChannelListResponse {
  channels: ChannelInfo[];
}

// New interface for Role info
export interface RoleInfo {
  id: string;
  name: string;
}

export interface GuildRolesResponse {
  roles: RoleInfo[];
}

export interface MessageItem {
  role: string;
  content: string;
  provider: string | null;
  type: string | null;
  created_at: string;
}

export interface GuildItem {
  id: string;
  name: string;
  member_count: number;
}

export interface BotStatus {
  online: boolean;
  username: string | null;
  latency: number | null;
  guild_count: number;
  guilds: GuildItem[];
  uptime: number | null;
}

export interface TestProviderResult {
  success: boolean;
  message: string;
  latency_ms?: number;
}

// FAQ interfaces
export interface FAQBase {
  question: string;
  answer: string;
  match_keywords: string;
}

// Analytics interfaces
export interface AnalyticsSummaryRow {
  day: string; // iso date
  event_type: string;
  count: number;
  tokens?: number;       // optional aggregated token count
  cost?: number;         // optional aggregated estimated cost
}

export interface AnalyticsEvent {
  id: number;
  event_type: string;
  guild_id: string | null;
  channel_id: string | null;
  user_id: string | null;
  provider: string | null;
  tokens_used: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  estimated_cost?: number | null;
  latency_ms: number | null;
  created_at: string;
}

export interface FAQCreate extends FAQBase {}

export interface FAQResponse extends FAQBase {
  id: number;
  guild_id: string;
  times_used: number;
  created_by: string | null;
  created_at: string;
}

// Command Permissions interfaces
export interface CommandPermissionBase {
  command_name: string;
  guild_id: string;
  role_id: string;
}

export interface CommandPermissionCreate extends CommandPermissionBase {}

export interface CommandPermissionResponse extends CommandPermissionBase {}

// Channel Prompt interfaces
export interface ChannelPromptBase {
  channel_id: string;
  guild_id: string;
  system_prompt: string;
}

export interface ChannelPromptCreate extends ChannelPromptBase {}

export interface ChannelPromptResponse extends ChannelPromptBase {}

// Plugin system types
export interface PluginInfo {
  name: string;
  version?: string;
  author?: string;
  description?: string;
  enabled: number;
}

export const api = {
  // Auth
  login: (password: string) =>
    apiFetch<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),

  me: (token: string) =>
    apiFetch<{ username: string; role: string }>("/api/auth/me", { token }),

  // Config
  getConfig: (token: string) =>
    apiFetch<{ config: Record<string, string> }>("/api/config", { token }),

  updateConfig: (token: string, values: Record<string, string>) =>
    apiFetch<{ status: string }>("/api/config", {
      method: "PUT",
      body: JSON.stringify({ values }),
      token,
    }),

  // Providers
  getProviders: (token: string) =>
    apiFetch<ProvidersResponse>("/api/providers", { token }),

  testProvider: (token: string, provider: string) =>
    apiFetch<TestProviderResult>("/api/providers/test", {
      method: "POST",
      body: JSON.stringify({ provider }),
      token,
    }),

  setPrimaryProvider: (token: string, provider: string) =>
    apiFetch<{ status: string; primary: string }>("/api/providers/primary", {
      method: "PUT",
      body: JSON.stringify({ provider }),
      token,
    }),

  // Bot
  getBotStatus: (token: string) =>
    apiFetch<BotStatus>("/api/bot/status", { token }),

  // Conversations
  getConversations: (token: string) =>
    apiFetch<{ channels: ChannelItem[] }>("/api/conversations", { token }),

  getConversation: (token: string, channelId: string) =>
    apiFetch<{ channel_id: string; messages: MessageItem[] }>(
      `/api/conversations/${channelId}`,
      { token }
    ),

  deleteConversation: (token: string, channelId: string) =>
    apiFetch<{ status: string }>(`/api/conversations/${channelId}`, {
      method: "DELETE",
      token,
    }),

  // Wizard
  getWizardStatus: (token: string) =>
    apiFetch<{ completed: boolean; current_step: number }>("/api/wizard/status", { token }),

  completeWizard: (token: string, data: Record<string, string>) =>
    apiFetch<{ status: string }>("/api/wizard/complete", {
      method: "POST",
      body: JSON.stringify({ config: data }),
      token,
    }),

  // FAQs
  listFaqs: (token: string, guildId: string | null = null) =>
    apiFetch<FAQResponse[]>("/api/faqs" + (guildId ? `?guild_id=${guildId}` : ""), { token }),

  // Analytics
  getAnalyticsSummary: (token: string) =>
    apiFetch<{ summary: AnalyticsSummaryRow[] }>("/api/analytics/summary", { token }),

  getAnalyticsHistory: (token: string, limit: number = 1000) =>
    apiFetch<{ history: AnalyticsEvent[] }>(
      `/api/analytics/history?limit=${limit}`,
      { token }
    ),

  // Quota & Rate Limiting
  getQuotaStatus: (token: string) =>
    apiFetch<{
      rate_limit_user: number;
      rate_limit_guild: number;
      quotas: { users: Record<string, any>; guilds: Record<string, any> };
    }>("/api/quota/status", { token }),

  // Plugins
  getPlugins: (token: string) =>
    apiFetch<{ plugins: PluginInfo[] }>("/api/plugins", { token }),

  enablePlugin: (token: string, name: string) =>
    apiFetch<{ status: string }>(`/api/plugins/${name}/enable`, {
      method: "POST",
      token,
    }),

  disablePlugin: (token: string, name: string) =>
    apiFetch<{ status: string }>(`/api/plugins/${name}/disable`, {
      method: "POST",
      token,
    }),
  
  // New: Upload plugin zip file
  uploadPluginZip: (token: string, file: File) => {
    const formData = new FormData();
    formData.append("plugin_zip_file", file); // Changed field name and single file
    return apiFetch<{ message: string; filenames: string[] }>("/api/plugins/upload", {
      method: "POST",
      body: formData,
      token,
      headers: {
        // When using FormData, fetch automatically sets 'Content-Type': 'multipart/form-data'
        // and its boundary. Explicitly setting it here can cause issues.
        // So, we'll omit Content-Type for FormData.
      },
    });
  },

  // New: Rescan plugins directory
  rescanPlugins: (token: string) =>
    apiFetch<{ message: string }>("/api/plugins/rescan", {
      method: "POST",
      token,
    }),
  
  // New: Delete plugin
  deletePlugin: (token: string, name: string) =>
    apiFetch<{ message: string }>(`/api/plugins/${name}`, {
      method: "DELETE",
      token,
    }),

  createFaq: (token: string, guildId: string, faq: FAQCreate) =>
    apiFetch<FAQResponse>(`/api/faqs?guild_id=${guildId}`, {
      method: "POST",
      body: JSON.stringify(faq),
      token,
    }),

  deleteFaq: (token: string, guildId: string, faqId: number) =>
    apiFetch<void>(`/api/faqs/${faqId}?guild_id=${guildId}`, {
      method: "DELETE",
      token,
    }),

  // Permissions
  listCommandPermissions: (token: string, guildId: string) =>
    apiFetch<CommandPermissionResponse[]>(`/api/permissions?guild_id=${guildId}`, { token }),

  createCommandPermission: (token: string, permission: CommandPermissionCreate) =>
    apiFetch<CommandPermissionResponse>("/api/permissions", {
      method: "POST",
      body: JSON.stringify(permission),
      token,
    }),

  deleteCommandPermission: (token: string, commandName: string, guildId: string, roleId: string) =>
    apiFetch<void>(`/api/permissions/${commandName}/${roleId}?guild_id=${guildId}`, {
      method: "DELETE",
      token,
    }),

  // Channel Prompts
  listChannelPrompts: (token: string) =>
    apiFetch<{ channel_prompts: ChannelPromptResponse[] }>("/api/config/channel_prompts", { token }),
  
  // guild channel listing (used for display names)
  listGuildChannels: (token: string, guildId: string) =>
    apiFetch<ChannelListResponse>(`/api/bot/guilds/${guildId}/channels`, { token }),
  
  // New: List guild roles
  listGuildRoles: (token: string, guildId: string) =>
    apiFetch<GuildRolesResponse>(`/api/bot/guilds/${guildId}/roles`, { token }),
  
  createChannelPrompt: (token: string, prompt: ChannelPromptCreate) =>
    apiFetch<{ status: string }>("/api/config/channel_prompts", {
      method: "POST",
      body: JSON.stringify(prompt),
      token,
    }),

  deleteChannelPrompt: (token: string, channelId: string) =>
    apiFetch<{ status: string }>(`/api/config/channel_prompts/${channelId}`, {
      method: "DELETE",
      token,
    }),

  // Channel Providers
  listChannelProviders: (token: string) =>
    apiFetch<{ channel_providers: ChannelProviderResponse[] }>("/api/config/channel_providers", { token }),
  
  createChannelProvider: (token: string, provider: ChannelProviderCreate) =>
    apiFetch<{ status: string }>("/api/config/channel_providers", {
      method: "POST",
      body: JSON.stringify(provider),
      token,
    }),

  deleteChannelProvider: (token: string, channelId: string) =>
    apiFetch<{ status: string }>(`/api/config/channel_providers/${channelId}`, {
      method: "DELETE",
      token,
    }),
};


// Channel Provider interfaces
export interface ChannelProviderBase {
  channel_id: string;
  guild_id: string;
  provider_name: string;
}

export interface ChannelProviderCreate extends ChannelProviderBase {}

export interface ChannelProviderResponse extends ChannelProviderBase {}