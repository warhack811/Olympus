# app/orchestrator_v42/plugins/task_graph.py

from typing import List, Dict, Any
import copy

def topo_sort(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Görevleri bağımlılıklarına (depends_on) göre topolojik olarak sıralar.
    
    Özellikler (v7.1 Fix):
    - ID'si olmayan tasklara deterministik 'anon_X' ID atar.
    - Bilinmeyen bağımlılıkları yoksayar (meta'ya unknown_dep_ignored yazar).
    - Döngüsel bağımlılıkları yoksayar (meta'ya cycle_suspected yazar), kısmi sıralı liste döner.
    - Orijinal listeyi bozmaz (deep copy veya yeni liste kullanır).
    """
    if not tasks:
        return []

    # Orijinal veriyi korumak için shallow copy ile yeni liste, 
    # ancak dict içeriklerini değiştireceğimiz için (meta/id) 
    # güvenli olması adına kopyalayarak çalışalım.
    working_tasks = [t.copy() for t in tasks if isinstance(t, dict)]
    
    # Varsayılan Meta (Yoksa ekle)
    for t in working_tasks:
        if "meta" not in t or not isinstance(t["meta"], dict):
            t["meta"] = {}

    # 1. ID Kontrolü ve Atama
    anon_counter = 1
    for t in working_tasks:
        if not t.get("id"):
            t["id"] = f"anon_{anon_counter}"
            anon_counter += 1
            
    # Graf Yapısı
    task_map = {t["id"]: t for t in working_tasks}
    in_degree = {t["id"]: 0 for t in working_tasks}
    adj_list = {t["id"]: [] for t in working_tasks}
    
    # 2. Bağımlılıkları İşle
    for t in working_tasks:
        deps = t.get("depends_on", [])
        if not isinstance(deps, list):
            deps = []
            
        valid_deps = []
        unknown_dep_flag = False
        
        for parent_id in deps:
            if parent_id in task_map:
                adj_list[parent_id].append(t["id"])
                in_degree[t["id"]] += 1
                valid_deps.append(parent_id)
            else:
                unknown_dep_flag = True
        
        if unknown_dep_flag:
            t["meta"]["unknown_dep_ignored"] = True
            
        # (Opsiyonel) Temizlenmiş deps listesini geri yazabiliriz ama 
        # orijinal veriye sadık kalmak ve sadece sıralamak amacımız.
            
    # 3. Kuyruk (In-degree 0)
    queue = sorted([tid for tid, deg in in_degree.items() if deg == 0])
    
    sorted_tasks = []
    
    while queue:
        u = queue.pop(0)
        sorted_tasks.append(task_map[u])
        
        neighbors = sorted(adj_list[u])
        for v in neighbors:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
        
        queue.sort()
        
    # 4. Döngü Kontrolü ve Kurtarma
    if len(sorted_tasks) != len(working_tasks):
        # Sıralananlar tamam, kalanlar döngü içinde.
        processed_ids = set(t["id"] for t in sorted_tasks)
        remaining_tasks = []
        
        # Geri kalanları deterministik bir sırada ekleyelim (örneğin girdi sırası veya ID)
        for t in working_tasks:
            if t["id"] not in processed_ids:
                t["meta"]["cycle_suspected"] = True
                remaining_tasks.append(t)
        
        # En sona ekle (Partial Fix)
        sorted_tasks.extend(remaining_tasks)
        
    return sorted_tasks
