"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { PlusCircle, Loader2, Trash } from "lucide-react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api"; // Assuming api.ts will be updated to include channel provider calls
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
  } from "@/components/ui/select";
import type { ProviderItem } from "@/lib/api";


// Interface for Channel Provider data
interface ChannelProviderResponse {
  channel_id: string;
  guild_id: string;
  provider_name: string;
}

export default function ChannelProviderManagementPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const { toast } = useToast();

  const [channelProviders, setChannelProviders] = useState<ChannelProviderResponse[]>([]);
  const [channelNames, setChannelNames] = useState<Record<string,string>>({});
  const [allProviders, setAllProviders] = useState<ProviderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newChannelId, setNewChannelId] = useState("");
  const [newProviderName, setNewProviderName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // TODO: Implement proper guild selection. For now, default to first guild returned by bot status.
  const [guildId, setGuildId] = useState<string>("");

  const token = (session as { accessToken?: string })?.accessToken;

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    const loadGuildInfo = async () => {
      try {
        const status = await api.getBotStatus(token);
        if (status.guilds && status.guilds.length > 0) {
          setGuildId(status.guilds[0].id);
        }
      } catch (e) {
        console.error("Failed to fetch bot status for guild id", e);
      }
    };

    const fetchAllData = async () => {
      try {
        setLoading(true);
        // Fetch all channel providers
        const channelProvidersResponse = await api.listChannelProviders(token);
        const validProviders = channelProvidersResponse.channel_providers.filter((p) => /^\d+$/.test(p.guild_id));
        if (validProviders.length !== channelProvidersResponse.channel_providers.length) {
          toast({
            title: "Warning",
            description: "Some channel providers had invalid guild IDs and were ignored. Please re-create them with a valid guild.",
            variant: "destructive",
          });
        }
        setChannelProviders(validProviders);

        // fetch channel names for each valid guild involved
        const guildIds = Array.from(new Set(
          channelProvidersResponse.channel_providers
            .map((p) => p.guild_id)
            .filter((id) => /^\d+$/.test(id))
        ));
        const namesMap: Record<string,string> = {};
        for (const gid of guildIds) {
          try {
            const chanResp = await api.listGuildChannels(token, gid);
            chanResp.channels.forEach((c) => {
              namesMap[c.id] = c.name;
            });
          } catch (e) {
            console.error("Failed to fetch channels for guild", gid, e);
          }
        }
        setChannelNames((prev) => ({ ...prev, ...namesMap }));

        // Fetch all available AI providers for the select dropdown
        const providersResponse = await api.getProviders(token);
        setAllProviders(providersResponse.providers.filter(p => p.configured)); // Only show configured providers
      } catch (err) {
        setError("Failed to fetch data.");
        console.error("Failed to fetch data:", err);
        toast({
          title: "Error",
          description: "Failed to fetch channel providers or AI providers.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };

    loadGuildInfo();
    fetchAllData();
  }, [token, toast]);

  const handleAddChannelProvider = async () => {
    if (!token || !guildId || !newChannelId || !newProviderName) {
      toast({
        title: "Error",
        description: "Please fill in all fields for the new channel provider.",
        variant: "destructive",
      });
      return;
    }

    setSubmitting(true);
    try {
      const newProvider = {
        channel_id: newChannelId,
        guild_id: guildId,
        provider_name: newProviderName,
      };
      await api.createChannelProvider(token, newProvider);
      setChannelProviders((prev) => [...prev, newProvider]); // Add to local state
      // update channel name map for the new entry
      try {
        const chanResp = await api.listGuildChannels(token, newProvider.guild_id);
        const ch = chanResp.channels.find((c) => c.id === newProvider.channel_id);
        if (ch) {
          setChannelNames((prev) => ({ ...prev, [ch.id]: ch.name }));
        }
      } catch (e) {
        console.error("couldn't fetch name for new channel provider", e);
      }
      setNewChannelId("");
      setNewProviderName("");
      toast({
        title: "Success",
        description: "Channel provider added successfully!",
      });
    } catch (err) {
      setError("Failed to add channel provider.");
      console.error("Failed to add channel provider:", err);
      toast({
        title: "Error",
        description: "Failed to add channel provider.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteChannelProvider = async (channelId: string) => {
    if (!token) {
      toast({
        title: "Error",
        description: "Authentication token is missing.",
        variant: "destructive",
      });
      return;
    }

    if (!confirm("Are you sure you want to delete this channel provider?")) {
      return;
    }

    try {
      await api.deleteChannelProvider(token, channelId);
      setChannelProviders((prev) => prev.filter((provider) => provider.channel_id !== channelId));
      toast({
        title: "Success",
        description: "Channel provider deleted successfully!",
      });
    } catch (err) {
      setError("Failed to delete channel provider.");
      console.error("Failed to delete channel provider:", err);
      toast({
        title: "Error",
        description: "Failed to delete channel provider.",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return <p className="text-red-500">{error}</p>;
  }

  if (!token) {
    return <p>Please log in to manage channel providers.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Channel Provider Management</h2>
        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <PlusCircle className="mr-2 h-4 w-4" /> Add New Channel Provider
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Add New Channel Provider</DialogTitle>
              <DialogDescription>
                Set a custom AI provider for a specific channel.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="channel-id" className="text-right">
                  Channel ID
                </Label>
                <Input
                  id="channel-id"
                  value={newChannelId}
                  onChange={(e) => setNewChannelId(e.target.value)}
                  className="col-span-3"
                  placeholder="e.g., 123456789012345678"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="provider-name" className="text-right">
                  AI Provider
                </Label>
                <Select value={newProviderName} onValueChange={setNewProviderName}>
                  <SelectTrigger id="provider-name" className="col-span-3">
                    <SelectValue placeholder="Select a provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {allProviders.map((provider) => (
                      <SelectItem key={provider.name} value={provider.name}>
                        {provider.display_name} ({provider.model})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleAddChannelProvider} disabled={submitting}>
                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add Channel Provider
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Existing Channel Providers</CardTitle>
          <CardDescription>
            Manage custom AI providers for individual channels.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">Channel</TableHead>
                <TableHead className="w-[180px]">Guild ID</TableHead>
                <TableHead>Provider Name</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {channelProviders.map((provider) => (
                <TableRow key={provider.channel_id}>
                  <TableCell className="font-medium">
                    {channelNames[provider.channel_id]
                      ? `${channelNames[provider.channel_id]} (${provider.channel_id})`
                      : provider.channel_id}
                  </TableCell>
                  <TableCell>{provider.guild_id}</TableCell>
                  <TableCell>{provider.provider_name}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteChannelProvider(provider.channel_id)}
                    >
                      <Trash className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}