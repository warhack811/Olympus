import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Badge } from "../../../components/ui/Badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/Table";
import { Trash2, Plus, Copy, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

// --- Mock API & Types ---
interface InviteCode {
    id: string;
    code: string;
    created_by: string;
    created_at: string;
    is_used: boolean;
    used_by?: string;
    used_at?: string;
}

const parseDate = (dateStr: string) => new Date(dateStr).toLocaleString();

const mockInvites = [
    { id: "1", code: "MAMI-2024-ALPHA", created_by: "admin", created_at: "2024-01-01T12:00:00Z", is_used: true, used_by: "early_adopter", used_at: "2024-01-02T10:30:00Z" },
    { id: "2", code: "MAMI-X9Y2-Z3A1", created_by: "admin", created_at: "2024-12-15T09:00:00Z", is_used: false },
    { id: "3", code: "VIP-ACCESS-007", created_by: "system", created_at: "2024-12-16T08:15:00Z", is_used: false },
];

export default function InvitesPage() {
    const [invites, setInvites] = useState<InviteCode[]>([]);
    const [loading, setLoading] = useState(true);
    const [newCode, setNewCode] = useState("");

    useEffect(() => {
        // Simulate API fetch
        setTimeout(() => {
            setInvites(mockInvites);
            setLoading(false);
        }, 600);
    }, []);

    const handleCreateInvite = () => {
        const code = newCode.trim() || `INV-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
        const newInvite: InviteCode = {
            id: Math.random().toString(),
            code: code,
            created_by: "admin", // In real app, get from auth context
            created_at: new Date().toISOString(),
            is_used: false,
        };

        setInvites([newInvite, ...invites]);
        setNewCode("");
    };

    const handleDeleteInvite = (id: string) => {
        if (confirm("Are you sure you want to delete this invite code?")) {
            setInvites(invites.filter((inv) => inv.id !== id));
        }
    };

    const copyToClipboard = (code: string) => {
        navigator.clipboard.writeText(code);
        // Could add toast notification here
    };

    return (
        <div className="space-y-6 p-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white">Invite Management</h1>
                    <p className="text-muted-foreground mt-2">Create and manage invitation codes for new user registration.</p>
                </div>
                <Button variant="outline" onClick={() => setLoading(true)}><RefreshCw className="w-4 h-4 mr-2" /> Refresh</Button>
            </div>

            {/* Create Invite Card */}
            <Card className="bg-card/50 backdrop-blur border-white/10">
                <CardHeader>
                    <CardTitle>Create New Invite</CardTitle>
                    <CardDescription>Generate a new code manually or automatically</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex gap-4">
                        <Input
                            placeholder="Enter custom code (optional)"
                            value={newCode}
                            onChange={(e) => setNewCode(e.target.value)}
                            className="max-w-md bg-background/50 border-white/10"
                        />
                        <Button onClick={handleCreateInvite} className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700">
                            <Plus className="w-4 h-4 mr-2" />
                            Generate Invite
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Invites List */}
            <Card className="bg-card/50 backdrop-blur border-white/10">
                <CardHeader>
                    <CardTitle>Active Invites</CardTitle>
                    <CardDescription>Manage existing invitation codes</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border border-white/10 overflow-hidden">
                        <Table>
                            <TableHeader className="bg-muted/50">
                                <TableRow className="border-white/10 hover:bg-transparent">
                                    <TableHead className="text-muted-foreground">Code</TableHead>
                                    <TableHead className="text-muted-foreground">Status</TableHead>
                                    <TableHead className="text-muted-foreground">Created By</TableHead>
                                    <TableHead className="text-muted-foreground">Created At</TableHead>
                                    <TableHead className="text-muted-foreground">Used By</TableHead>
                                    <TableHead className="text-right text-muted-foreground">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {invites.map((invite, index) => (
                                    <motion.tr
                                        key={invite.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="border-white/10 hover:bg-white/5 transition-colors"
                                    >
                                        <TableCell className="font-mono font-medium text-blue-400">
                                            {invite.code}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={`${invite.is_used ? "bg-red-500/10 text-red-400 border-red-500/20" : "bg-green-500/10 text-green-400 border-green-500/20"}`}>
                                                {invite.is_used ? "Used" : "Available"}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>{invite.created_by}</TableCell>
                                        <TableCell className="text-muted-foreground text-sm">{parseDate(invite.created_at)}</TableCell>
                                        <TableCell>
                                            {invite.is_used ? (
                                                <div className="flex flex-col">
                                                    <span className="font-medium text-white">{invite.used_by}</span>
                                                    <span className="text-xs text-muted-foreground">{invite.used_at ? parseDate(invite.used_at) : ""}</span>
                                                </div>
                                            ) : (
                                                <span className="text-muted-foreground">-</span>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex justify-end gap-2">
                                                <Button variant="ghost" size="icon" onClick={() => copyToClipboard(invite.code)} title="Copy Code">
                                                    <Copy className="w-4 h-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                                                    onClick={() => handleDeleteInvite(invite.id)}
                                                    title="Delete Invite"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </motion.tr>
                                ))}
                                {invites.length === 0 && !loading && (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                            No invites found. Create one above.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
