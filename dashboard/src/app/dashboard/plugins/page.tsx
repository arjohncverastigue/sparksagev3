"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { api, PluginInfo } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/use-toast";
import { Loader2 } from "lucide-react";

export default function PluginManagementPage() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken;
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    setLoading(true);
    api
      .getPlugins(token)
      .then((data) => setPlugins(data.plugins))
      .catch((err) => {
        console.error(err);
        toast({
          title: "Error",
          description: "Failed to load plugins.",
          variant: "destructive",
        });
      })
      .finally(() => setLoading(false));
  }, [token, toast]);

  const togglePlugin = async (name: string, currentlyEnabled: boolean) => {
    if (!token) return;
    try {
      if (currentlyEnabled) {
        await api.disablePlugin(token, name);
      } else {
        await api.enablePlugin(token, name);
      }
      setPlugins((prev) =>
        prev.map((p) =>
          p.name === name ? { ...p, enabled: currentlyEnabled ? 0 : 1 } : p
        )
      );
    } catch (err) {
      console.error(err);
      toast({
        title: "Error",
        description: `Failed to ${currentlyEnabled ? "disable" : "enable"} plugin.`,
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return <Loader2 className="h-8 w-8 animate-spin" />;
  }

  if (!token) {
    return <p>Please log in to manage plugins.</p>;
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Plugin Management</h1>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="hidden sm:table-cell">Description</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {plugins.map((p) => (
            <TableRow key={p.name}>
              <TableCell>{p.name}</TableCell>
              <TableCell className="hidden sm:table-cell">
                {p.description || "-"}
              </TableCell>
              <TableCell>{p.enabled ? "Enabled" : "Disabled"}</TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant={p.enabled ? "destructive" : "default"}
                  onClick={() => togglePlugin(p.name, !!p.enabled)}
                >
                  {p.enabled ? "Disable" : "Enable"}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
