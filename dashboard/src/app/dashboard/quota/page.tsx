"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { api, GuildItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";

type QuotaData = {
  rate_limit_user: number;
  rate_limit_guild: number;
  quotas: {
    users: Record<string, { tokens_remaining: number; reset_at: number }>;
    guilds: Record<string, { tokens_remaining: number; reset_at: number }>;
  };
};

export default function QuotaPage() {
  const { data: session } = useSession();
  const [quotaData, setQuotaData] = useState<QuotaData | null>(null);
  const [guildNamesMap, setGuildNamesMap] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(true);
  const [isUserLimitEditing, setIsUserLimitEditing] = useState(false);
  const [userLimitInput, setUserLimitInput] = useState("");
  const [isGuildLimitEditing, setIsGuildLimitEditing] = useState(false);
  const [guildLimitInput, setGuildLimitInput] = useState("");
  const { toast } = useToast();
  const token = (session as { accessToken?: string })?.accessToken;

  const handleEditUserLimit = () => {
    setIsUserLimitEditing(true);
    setUserLimitInput(String(quotaData?.rate_limit_user || ""));
  };

  const handleSaveUserLimit = async () => {
    if (!token || !quotaData) return;
    const newValue = Number(userLimitInput);
    if (isNaN(newValue) || newValue <= 0) {
      toast({
        title: "Invalid input",
        description: "Please enter a valid positive number for the user limit.",
        variant: "destructive",
      });
      return;
    }

    try {
      await api.updateConfig(token, { RATE_LIMIT_USER: String(newValue) });
      setQuotaData((prev) => ({
        ...(prev as QuotaData),
        rate_limit_user: newValue,
      }));
      toast({
        title: "User limit updated successfully",
      });
    } catch (error) {
      toast({
        title: "Failed to update user limit",
        description: error instanceof Error ? error.message : "An unexpected error occurred.",
        variant: "destructive",
      });
    } finally {
      setIsUserLimitEditing(false);
    }
  };

  const handleCancelUserLimit = () => {
    setIsUserLimitEditing(false);
    setUserLimitInput("");
  };

  const handleEditGuildLimit = () => {
    setIsGuildLimitEditing(true);
    setGuildLimitInput(String(quotaData?.rate_limit_guild || ""));
  };

  const handleSaveGuildLimit = async () => {
    if (!token || !quotaData) return;
    const newValue = Number(guildLimitInput);
    if (isNaN(newValue) || newValue <= 0) {
      toast({
        title: "Invalid input",
        description: "Please enter a valid positive number for the guild limit.",
        variant: "destructive",
      });
      return;
    }

    try {
      await api.updateConfig(token, { RATE_LIMIT_GUILD: String(newValue) });
      setQuotaData((prev) => ({
        ...(prev as QuotaData),
        rate_limit_guild: newValue,
      }));
      toast({
        title: "Guild limit updated successfully",
      });
    } catch (error) {
      toast({
        title: "Failed to update guild limit",
        description: error instanceof Error ? error.message : "An unexpected error occurred.",
        variant: "destructive",
      });
    } finally {
      setIsGuildLimitEditing(false);
    }
  };

  const handleCancelGuildLimit = () => {
    setIsGuildLimitEditing(false);
    setGuildLimitInput("");
  };

  useEffect(() => {
    if (!token) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [quotaResponse, botStatusResponse] = await Promise.all([
          api.getQuotaStatus(token),
          api.getBotStatus(token),
        ]);

        setQuotaData(quotaResponse);

        const newGuildNamesMap = new Map<string, string>();
        botStatusResponse.guilds.forEach((guild: GuildItem) => {
          newGuildNamesMap.set(guild.id, guild.name);
        });
        setGuildNamesMap(newGuildNamesMap);
      } catch (error) {
        console.error("Failed to fetch quota or bot status:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-12 w-48" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!quotaData) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        Unable to load quota information
      </div>
    );
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  const formatTime = (unixTime: number) => {
    const now = Date.now() / 1000;
    const diff = Math.max(0, unixTime - now);

    if (diff < 60) return `${Math.ceil(diff)}s`;
    if (diff < 3600) return `${Math.ceil(diff / 60)}m`;
    return `${Math.ceil(diff / 3600)}h`;
  };

  const getProgressValue = (
    used: number,
    capacity: number
  ) => {
    return Math.round((used / capacity) * 100);
  };

  const userQuotas = Object.entries(quotaData.quotas.users).sort(
    ([, a], [, b]) =>
      a.tokens_remaining - b.tokens_remaining
  );
  const guildQuotas = Object.entries(quotaData.quotas.guilds).sort(
    ([, a], [, b]) =>
      a.tokens_remaining - b.tokens_remaining
  );

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Rate Limiting & Quotas</h1>
        <p className="text-muted-foreground mt-2">
          Monitor your API usage and rate limits
        </p>
      </div>

      {/* Limits Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Per-User Limit
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isUserLimitEditing ? (
              <div className="flex items-center space-x-2">
                <Input
                  type="number"
                  value={userLimitInput}
                  onChange={(e) => setUserLimitInput(e.target.value)}
                  className="w-24"
                />
                <Button size="sm" onClick={handleSaveUserLimit}>Save</Button>
                <Button variant="outline" size="sm" onClick={handleCancelUserLimit}>Cancel</Button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="text-2xl font-bold">
                  {quotaData.rate_limit_user}
                </div>
                <Button variant="outline" size="sm" onClick={handleEditUserLimit}>Edit</Button>
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              requests per minute
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Per-Guild Limit
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isGuildLimitEditing ? (
              <div className="flex items-center space-x-2">
                <Input
                  type="number"
                  value={guildLimitInput}
                  onChange={(e) => setGuildLimitInput(e.target.value)}
                  className="w-24"
                />
                <Button size="sm" onClick={handleSaveGuildLimit}>Save</Button>
                <Button variant="outline" size="sm" onClick={handleCancelGuildLimit}>Cancel</Button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="text-2xl font-bold">
                  {quotaData.rate_limit_guild}
                </div>
                <Button variant="outline" size="sm" onClick={handleEditGuildLimit}>Edit</Button>
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              requests per minute
            </p>
          </CardContent>
        </Card>
      </div>

      {/* User Quotas */}
      <Card>
        <CardHeader>
          <CardTitle>Active Users ({userQuotas.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {userQuotas.length === 0 ? (
            <p className="text-muted-foreground text-sm">No active users</p>
          ) : (
            <div className="space-y-4">
              {userQuotas.map(([userId, quota]) => {
                const used = quotaData.rate_limit_user - quota.tokens_remaining;
                const progress = getProgressValue(
                  Math.max(0, used),
                  quotaData.rate_limit_user
                );
                const isLimited = quota.tokens_remaining === 0;

                return (
                  <div key={userId} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium truncate">
                        {userId}
                      </span>
                      <span
                        className={`text-xs font-semibold ${
                          isLimited
                            ? "text-red-500"
                            : progress > 80
                              ? "text-orange-500"
                              : "text-green-500"
                        }`}
                      >
                        {quota.tokens_remaining}/{quotaData.rate_limit_user}
                      </span>
                    </div>
                    <Progress value={progress} className="h-2" />
                    <div className="text-xs text-muted-foreground">
                      {isLimited
                        ? `Reset in ${formatTime(quota.reset_at)}`
                        : `${Math.max(0, quota.tokens_remaining)} requests remaining`}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Guild Quotas */}
      <Card>
        <CardHeader>
          <CardTitle>Active Guilds ({guildQuotas.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {guildQuotas.length === 0 ? (
            <p className="text-muted-foreground text-sm">No active guilds</p>
          ) : (
            <div className="space-y-4">
              {guildQuotas.map(([guildId, quota]) => {
                const used = quotaData.rate_limit_guild - quota.tokens_remaining;
                const progress = getProgressValue(
                  Math.max(0, used),
                  quotaData.rate_limit_guild
                );
                const isLimited = quota.tokens_remaining === 0;

                return (
                  <div key={guildId} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium truncate">
                        {guildNamesMap.get(guildId) || guildId}
                      </span>
                      <span
                        className={`text-xs font-semibold ${
                          isLimited
                            ? "text-red-500"
                            : progress > 80
                              ? "text-orange-500"
                              : "text-green-500"
                        }`}
                      >
                        {quota.tokens_remaining}/{quotaData.rate_limit_guild}
                      </span>
                    </div>
                    <Progress value={progress} className="h-2" />
                    <div className="text-xs text-muted-foreground">
                      {isLimited
                        ? `Reset in ${formatTime(quota.reset_at)}`
                        : `${Math.max(0, quota.tokens_remaining)} requests remaining`}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
