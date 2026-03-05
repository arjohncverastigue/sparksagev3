"use client";

import { useEffect, useState, ChangeEvent } from "react";
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
import { Loader2, Upload, RotateCw, Trash2 } from "lucide-react"; // Import Trash2 icon

export default function PluginManagementPage() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken;
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [rescanning, setRescanning] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [deletingPlugin, setDeletingPlugin] = useState<string | null>(null); // State to track which plugin is being deleted
  const { toast } = useToast();

  const fetchPlugins = async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.getPlugins(token);
      setPlugins(data.plugins);
    } catch (err) {
      console.error(err);
      toast({
        title: "Error",
        description: "Failed to load plugins.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlugins();
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
      toast({
        title: "Success",
        description: `Plugin ${name} ${currentlyEnabled ? "disabled" : "enabled"}.`,
      });
    } catch (err) {
      console.error(err);
      toast({
        title: "Error",
        description: `Failed to ${currentlyEnabled ? "disable" : "enable"} plugin.`,
        variant: "destructive",
      });
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFiles(event.target.files);
  };

  const handleUpload = async () => {
    if (!token || !selectedFiles || selectedFiles.length === 0) {
      toast({
        title: "Warning",
        description: "Please select at least one file to upload.",
        variant: "destructive",
      });
      return;
    }

    setUploading(true);
    try {
      const filesArray = Array.from(selectedFiles);
      const response = await api.uploadPluginFiles(token, filesArray);
      toast({
        title: "Success",
        description: response.message,
      });
      setSelectedFiles(null);
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      await fetchPlugins();
    } catch (err: any) {
      console.error(err);
      toast({
        title: "Error",
        description: `Failed to upload plugin files: ${err.message || "Unknown error"}`,
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleRescan = async () => {
    if (!token) return;
    setRescanning(true);
    try {
      const response = await api.rescanPlugins(token);
      toast({
        title: "Success",
        description: response.message,
      });
      await fetchPlugins();
    } catch (err: any) {
      console.error(err);
      toast({
        title: "Error",
        description: `Failed to rescan plugins: ${err.message || "Unknown error"}`,
        variant: "destructive",
      });
    } finally {
      setRescanning(false);
    }
  };

  const handleDeletePlugin = async (name: string) => {
    if (!token) return;

    if (!confirm(`Are you sure you want to delete the plugin '${name}'? This action cannot be undone.`)) {
      return;
    }

    setDeletingPlugin(name);
    try {
      const response = await api.deletePlugin(token, name);
      toast({
        title: "Success",
        description: response.message,
      });
      await fetchPlugins();
    } catch (err: any) {
      console.error(err);
      toast({
        title: "Error",
        description: `Failed to delete plugin '${name}': ${err.message || "Unknown error"}`,
        variant: "destructive",
      });
    } finally {
      setDeletingPlugin(null);
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

      <div className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-4 p-4 border rounded-md bg-card text-card-foreground shadow-sm">
        <label htmlFor="plugin-upload" className="sr-only">Upload Plugin Files</label>
        <input
          id="plugin-upload"
          type="file"
          multiple
          accept=".json,.py"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-violet-50 file:text-violet-700
            hover:file:bg-violet-100"
        />
        <Button onClick={handleUpload} disabled={uploading || !selectedFiles || selectedFiles.length === 0}>
          {uploading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Upload className="mr-2 h-4 w-4" />
          )}
          Upload Plugin(s)
        </Button>
        <Button onClick={handleRescan} disabled={rescanning}>
          {rescanning ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RotateCw className="mr-2 h-4 w-4" />
          )}
          Rescan Plugins
        </Button>
      </div>

      {selectedFiles && selectedFiles.length > 0 && (
        <div className="text-sm text-gray-600">
          Selected files: {Array.from(selectedFiles).map(f => f.name).join(", ")}
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="hidden sm:table-cell">Description</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-[100px] text-right">Actions</TableHead>
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
              <TableCell className="flex justify-end space-x-2">
                <Button
                  size="sm"
                  variant={p.enabled ? "destructive" : "default"}
                  onClick={() => togglePlugin(p.name, !!p.enabled)}
                >
                  {p.enabled ? "Disable" : "Enable"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleDeletePlugin(p.name)}
                  disabled={deletingPlugin === p.name}
                >
                  {deletingPlugin === p.name ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                  <span className="sr-only">Delete {p.name}</span>
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}