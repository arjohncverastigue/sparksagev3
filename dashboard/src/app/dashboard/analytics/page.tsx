"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { api } from "@/lib/api";
import type { AnalyticsSummaryRow, AnalyticsEvent } from "@/lib/api";
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

export default function AnalyticsPage() {
  const { data: session } = useSession();
  const [summary, setSummary] = useState<AnalyticsSummaryRow[]>([]);
  const [history, setHistory] = useState<AnalyticsEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const token = (session as { accessToken?: string })?.accessToken;

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    Promise.all([
      api.getAnalyticsSummary(token),
      api.getAnalyticsHistory(token),
    ])
      .then(([summaryRes, historyRes]) => {
        setSummary(summaryRes.summary);
        setHistory(historyRes.history);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  // Prepare data for "Messages per day" line chart
  const messagesPerDay = summary
    .filter((row) => row.event_type === "ai_call" || row.event_type === "command")
    .reduce(
      (acc, row) => {
        const existing = acc.find((item) => item.date === row.day);
        if (existing) {
          existing.count += row.count;
        } else {
          acc.push({ date: row.day, count: row.count });
        }
        return acc;
      },
      [] as { date: string; count: number }[]
    )
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  // Prepare data for "Provider usage distribution" pie chart (by count)
  const providerUsage: { [key: string]: number } = {};
  history.forEach((evt) => {
    if (evt.provider) {
      providerUsage[evt.provider] = (providerUsage[evt.provider] || 0) + 1;
    }
  });
  const providerData = Object.entries(providerUsage).map(([name, count]) => ({
    name,
    value: count,
  }));

  // Prepare cost by provider (requires estimated_cost field)
  const costByProvider: { [key: string]: number } = {};
  history.forEach((evt) => {
    if (evt.provider && evt.estimated_cost != null) {
      costByProvider[evt.provider] =
        (costByProvider[evt.provider] || 0) + evt.estimated_cost;
    }
  });
  const costProviderData = Object.entries(costByProvider).map(([name, cost]) => ({
    name,
    cost,
  }));

  // Prepare data for "Top channels by activity" bar chart
  const channelActivity: { [key: string]: number } = {};
  history.forEach((evt) => {
    if (evt.channel_id) {
      channelActivity[evt.channel_id] = (channelActivity[evt.channel_id] || 0) + 1;
    }
  });
  const topChannels = Object.entries(channelActivity)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([id, count]) => ({ channel: id, events: count }));

  // Prepare data for "Average response latency" line chart
  const latencyByDay: { [key: string]: { total: number; count: number } } = {};
  history.forEach((evt) => {
    if (evt.latency_ms != null) {
      if (!latencyByDay[evt.created_at.split("T")[0]]) {
        latencyByDay[evt.created_at.split("T")[0]] = { total: 0, count: 0 };
      }
      latencyByDay[evt.created_at.split("T")[0]].total += evt.latency_ms;
      latencyByDay[evt.created_at.split("T")[0]].count += 1;
    }
  });
  const latencyData = Object.entries(latencyByDay)
    .map(([date, data]) => ({
      date,
      avgLatency: Math.round(data.total / data.count),
    }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  // Prepare data for tokens and cost per day using summary rows
  const tokensByDay: { [key: string]: number } = {};
  const costByDay: { [key: string]: number } = {};
  summary.forEach((row) => {
    if (row.tokens != null) {
      tokensByDay[row.day] = (tokensByDay[row.day] || 0) + row.tokens;
    }
    if (row.cost != null) {
      costByDay[row.day] = (costByDay[row.day] || 0) + row.cost;
    }
  });
  const tokensData = Object.entries(tokensByDay)
    .map(([date, total]) => ({ date, tokens: total }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  const costData = Object.entries(costByDay)
    .map(([date, total]) => ({ date, cost: total }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  // Calculate projected monthly cost (average of available data days)
  const totalCost = costData.reduce((sum, item) => sum + item.cost, 0);
  const avgDailyCost = costData.length > 0 ? totalCost / costData.length : 0;
  const projectedMonthlyCost = avgDailyCost * 30;
  const costThreshold = 50.0; // Default threshold; can be configured via env var
  const isApproachingThreshold = projectedMonthlyCost > costThreshold * 0.8; // Warn at 80% of threshold

  if (loading) {
    return <div className="text-center py-8">Loading analytics...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl sm:text-2xl font-bold">Analytics</h1>

      {/* Cost Alert Banner */}
      {isApproachingThreshold && (
        <div className="relative w-full rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold mb-1">Cost Alert</h3>
              <p>
                Projected monthly cost (${projectedMonthlyCost.toFixed(2)}) is approaching your threshold of ${costThreshold.toFixed(2)}. Consider optimizing your provider settings.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Cost Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Today's Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">
              ${costData.length > 0 ? costData[costData.length - 1].cost.toFixed(2) : "0.00"}
            </div>
            <p className="text-sm text-muted-foreground mt-2">Current day estimated cost</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Projected Monthly Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${isApproachingThreshold ? "text-red-600" : "text-green-600"}`}>
              ${projectedMonthlyCost.toFixed(2)}
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Based on avg daily cost of ${avgDailyCost.toFixed(2)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Messages per day */}
      <Card>
        <CardHeader>
          <CardTitle>Messages per Day</CardTitle>
        </CardHeader>
        <CardContent>
          {messagesPerDay.length === 0 ? (
            <p className="text-sm text-muted-foreground">No data available</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={messagesPerDay}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Tokens used per day */}
      <Card>
        <CardHeader>
          <CardTitle>Tokens Used per Day</CardTitle>
        </CardHeader>
        <CardContent>
          {tokensData.length === 0 ? (
            <p className="text-sm text-muted-foreground">No token data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={tokensData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="tokens" stroke="#6366f1" name="Tokens" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Estimated cost per day */}
      <Card>
        <CardHeader>
          <CardTitle>Estimated Cost per Day</CardTitle>
        </CardHeader>
        <CardContent>
          {costData.length === 0 ? (
            <p className="text-sm text-muted-foreground">No cost data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={costData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="cost" stroke="#ef4444" name="Cost ($)" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Provider usage distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Provider Usage Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          {providerData.length === 0 ? (
            <p className="text-sm text-muted-foreground">No provider data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={providerData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {providerData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Cost by provider */}
      <Card>
        <CardHeader>
          <CardTitle>Estimated Cost by Provider</CardTitle>
        </CardHeader>
        <CardContent>
          {costProviderData.length === 0 ? (
            <p className="text-sm text-muted-foreground">No cost data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={costProviderData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(value) => `$${Number(value).toFixed(2)}`} />
                <Legend />
                <Bar dataKey="cost" fill="#ef4444" name="Cost ($)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Top channels by activity */}
      <Card>
        <CardHeader>
          <CardTitle>Top Channels by Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {topChannels.length === 0 ? (
            <p className="text-sm text-muted-foreground">No channel data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topChannels}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="channel" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="events" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Average response latency */}
      <Card>
        <CardHeader>
          <CardTitle>Average Response Latency</CardTitle>
        </CardHeader>
        <CardContent>
          {latencyData.length === 0 ? (
            <p className="text-sm text-muted-foreground">No latency data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={latencyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="avgLatency"
                  stroke="#f59e0b"
                  name="Avg Latency (ms)"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
