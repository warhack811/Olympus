
import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/Dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Plus, Trash2, Edit2, Key, AlertTriangle, Eye, EyeOff, Copy, Check } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ApiKeyStats {
    key_name: string;
    masked_value: string;
}

export function ApiKeysManager() {
    const [keys, setKeys] = useState<ApiKeyStats[]>([]);
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);
    const [formData, setFormData] = useState({ key_name: '', value: '' });
    const [revealedKeys, setRevealedKeys] = useState<Record<string, string>>({});
    const [copiedKey, setCopiedKey] = useState<string | null>(null);
    const { toast } = useToast();

    const fetchKeys = async () => {
        try {
            setLoading(true);
            const res = await fetch('/api/v1/admin/api-keys');
            if (!res.ok) throw new Error('Failed');
            const data = await res.json();
            setKeys(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    React.useEffect(() => {
        fetchKeys();
    }, []);

    const handleSave = async () => {
        if (!formData.key_name || !formData.value) return;

        try {
            const res = await fetch('/api/v1/admin/api-keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!res.ok) throw new Error('Kaydedilemedi');

            toast({ title: "Başarılı", description: "Anahtar güncellendi." });
            setOpen(false);
            setFormData({ key_name: '', value: '' });
            fetchKeys();
            // Reload page recommendation
            toast({ title: "Hatırlatma", description: "Değişikliklerin işlemesi için servisi yeniden başlatmanız önerilir.", variant: "warning" });
        } catch (e) {
            toast({ title: "Hata", description: "İşlem başarısız.", variant: "destructive" });
        }
    };

    const handleDelete = async (keyName: string) => {
        if (!confirm(`${keyName} silinecek. Emin misiniz?`)) return;

        try {
            const res = await fetch(`/api/v1/admin/api-keys/${keyName}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Silinemedi');
            toast({ title: "Silindi", description: "Anahtar kaldırıldı." });
            fetchKeys();
        } catch (e) {
            toast({ title: "Hata", description: "Silme işlemi başarısız.", variant: "destructive" });
        }
    };

    const startEdit = (k: ApiKeyStats) => {
        setFormData({ key_name: k.key_name, value: '' }); // Value is kept empty for security
        setOpen(true);
    };

    const handleReveal = async (keyName: string) => {
        // Toggle - if already revealed, hide it
        if (revealedKeys[keyName]) {
            setRevealedKeys(prev => {
                const next = { ...prev };
                delete next[keyName];
                return next;
            });
            return;
        }

        try {
            const res = await fetch(`/api/v1/admin/api-keys/${keyName}/reveal`);
            if (!res.ok) throw new Error('Reveal failed');
            const data = await res.json();
            setRevealedKeys(prev => ({ ...prev, [keyName]: data.value }));
        } catch (e) {
            toast({ title: "Hata", description: "Anahtar görüntülenemedi.", variant: "destructive" });
        }
    };

    const handleCopy = async (keyName: string) => {
        const value = revealedKeys[keyName];
        if (!value) return;

        try {
            await navigator.clipboard.writeText(value);
            setCopiedKey(keyName);
            setTimeout(() => setCopiedKey(null), 2000);
            toast({ title: "Kopyalandı", description: "Anahtar panoya kopyalandı." });
        } catch {
            toast({ title: "Hata", description: "Kopyalanamadı.", variant: "destructive" });
        }
    };

    return (
        <Card className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-medium text-foreground">Anahtar Yönetimi</h3>
                    <p className="text-sm text-muted-foreground">Groq API anahtarlarını ekle veya düzenle.</p>
                </div>
                <Dialog open={open} onOpenChange={setOpen}>
                    <DialogTrigger asChild>
                        <Button onClick={() => setFormData({ key_name: 'GROQ_API_KEY_', value: '' })}>
                            <Plus className="w-4 h-4 mr-2" /> Yeni Ekle
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>API Anahtarı Düzenle</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium leading-none">Anahtar Adı (.env Key)</label>
                                <Input
                                    value={formData.key_name}
                                    onChange={e => setFormData({ ...formData, key_name: e.target.value })}
                                    placeholder="GROQ_API_KEY_5"
                                />
                                <p className="text-xs text-muted-foreground">Örn: GROQ_API_KEY, GROQ_API_KEY_BACKUP</p>
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium leading-none">Anahtar Değeri (Value)</label>
                                <Input
                                    value={formData.value}
                                    onChange={e => setFormData({ ...formData, value: e.target.value })}
                                    type="password"
                                    placeholder="gsk_..."
                                />
                            </div>
                            <div className="bg-yellow-500/10 p-3 rounded-md flex items-start gap-2 text-sm text-yellow-600 dark:text-yellow-400">
                                <AlertTriangle className="w-4 h-4 mt-0.5" />
                                <span>Bu işlem sunucudaki .env dosyasını günceller. Değişikliklerin tam olarak yansıması için sunucu yeniden başlatılmalıdır.</span>
                            </div>
                            <Button onClick={handleSave} className="w-full">Kaydet</Button>
                        </div>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="border rounded-md overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Anahtar Adı</TableHead>
                            <TableHead>Mevcut Değer (Maskeli)</TableHead>
                            <TableHead className="text-right">İşlemler</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {keys.map((k) => (
                            <TableRow key={k.key_name}>
                                <TableCell className="font-medium flex items-center gap-2">
                                    <Key className="w-4 h-4 text-muted-foreground" />
                                    {k.key_name}
                                </TableCell>
                                <TableCell className="font-mono text-xs">
                                    {revealedKeys[k.key_name] ? (
                                        <span className="text-green-500 break-all">{revealedKeys[k.key_name]}</span>
                                    ) : (
                                        k.masked_value
                                    )}
                                </TableCell>
                                <TableCell className="text-right space-x-1">
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleReveal(k.key_name)}
                                        title={revealedKeys[k.key_name] ? "Gizle" : "Göster"}
                                    >
                                        {revealedKeys[k.key_name] ? (
                                            <EyeOff className="w-4 h-4" />
                                        ) : (
                                            <Eye className="w-4 h-4" />
                                        )}
                                    </Button>
                                    {revealedKeys[k.key_name] && (
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => handleCopy(k.key_name)}
                                            title="Kopyala"
                                        >
                                            {copiedKey === k.key_name ? (
                                                <Check className="w-4 h-4 text-green-500" />
                                            ) : (
                                                <Copy className="w-4 h-4" />
                                            )}
                                        </Button>
                                    )}
                                    <Button variant="ghost" size="icon" onClick={() => startEdit(k)}>
                                        <Edit2 className="w-4 h-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" onClick={() => handleDelete(k.key_name)} className="text-red-500 hover:text-red-600">
                                        <Trash2 className="w-4 h-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                        {keys.length === 0 && !loading && (
                            <TableRow>
                                <TableCell colSpan={3} className="text-center text-muted-foreground h-24">
                                    Kayıtlı anahtar yok.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        </Card>
    );
}
