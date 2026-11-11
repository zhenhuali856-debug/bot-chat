import json
import os
import re
import shutil
from typing import Any, Dict, List, Optional
from app.core.memory import memory_manager

MANIFEST_WORKS_FILE = ".rabbit_works_manifest.json"
MANIFEST_CHAPTERS_FILE = ".rabbit_sync_manifest.json"
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


class LocalSyncManager:
    """
    本地目录同步管理器
    将数据库中的作品设定与正文章节按清晰目录结构同步到本地电脑文件夹
    """

    @staticmethod
    def get_default_sync_dir() -> str:
        return os.path.join(os.path.expanduser("~"), "Documents", "RabbitWorks")

    @staticmethod
    def sanitize_name(name: str, fallback: str = "未命名") -> str:
        """清理 Windows/macOS/Linux 非法文件名字符"""
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or "").strip())
        cleaned = cleaned.strip(" .")
        if not cleaned or cleaned.upper() in WINDOWS_RESERVED_NAMES:
            return fallback
        return cleaned[:80]

    @staticmethod
    def _read_json_file(path: str, default: Any) -> Any:
        if not os.path.isfile(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    @staticmethod
    def _write_json_file(path: str, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_sync_settings(self) -> Dict[str, Any]:
        """读取本地同步配置"""
        default_dir = self.get_default_sync_dir()
        with memory_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value FROM bot_settings WHERE key IN ('sync_dir', 'sync_auto', 'sync_format')"
            )
            rows = {r["key"]: r["value"] for r in cursor.fetchall()}

        sync_dir = (rows.get("sync_dir") or default_dir).strip()
        auto_sync = rows.get("sync_auto", "false").lower() == "true"
        file_format = rows.get("sync_format", "md")
        if file_format not in ("md", "txt"):
            file_format = "md"

        return {
            "sync_dir": sync_dir,
            "auto_sync": auto_sync,
            "file_format": file_format,
            "default_dir": default_dir,
            "dir_exists": os.path.isdir(sync_dir) if sync_dir else False,
        }

    def update_sync_settings(
        self, sync_dir: str, auto_sync: bool = True, file_format: str = "md"
    ) -> Dict[str, Any]:
        """更新并校验本地同步目录配置"""
        normalized_dir = os.path.abspath(os.path.expanduser(sync_dir.strip()))
        fmt = file_format if file_format in ("md", "txt") else "md"
        os.makedirs(normalized_dir, exist_ok=True)

        with memory_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('sync_dir', ?)",
                (normalized_dir,),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('sync_auto', ?)",
                ("true" if auto_sync else "false",),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('sync_format', ?)",
                (fmt,),
            )
            conn.commit()

        return self.get_sync_settings()

    def _format_work_meta(self, work: Dict[str, Any], ext: str) -> str:
        title = work.get("title") or "未命名作品"
        genre = work.get("genre") or "未指定"
        target_words = work.get("target_words") or 0
        summary = work.get("summary") or "暂无"
        outline = work.get("outline") or "暂无"

        if ext == "md":
            return (
                f"# 《{title}》作品设定与大纲\n\n"
                f"- **体裁**：{genre}\n"
                f"- **目标字数**：{target_words:,} 字\n\n"
                f"## 作品简介 / 世界观\n\n{summary}\n\n"
                f"## 故事大纲\n\n{outline}\n"
            )
        return (
            f"《{title}》作品设定与大纲\n"
            f"==============================\n"
            f"体裁：{genre}\n"
            f"目标字数：{target_words:,} 字\n\n"
            f"[作品简介 / 世界观]\n{summary}\n\n"
            f"[故事大纲]\n{outline}\n"
        )

    def _format_chapter_content(self, chapter: Dict[str, Any], ext: str) -> str:
        title = chapter.get("title") or "未命名章节"
        content = chapter.get("content") or ""
        if ext == "md":
            stripped = content.lstrip()
            if stripped.startswith("# "):
                return content
            return f"# {title}\n\n{content}\n"
        return f"{title}\n==============================\n\n{content}\n"

    def _ensure_sync_dir(self, sync_dir: Optional[str] = None) -> str:
        settings = self.get_sync_settings()
        target_dir = (sync_dir or settings["sync_dir"] or "").strip()
        if not target_dir:
            raise ValueError("尚未设置本地同步目录")
        resolved = os.path.abspath(os.path.expanduser(target_dir))
        os.makedirs(resolved, exist_ok=True)
        return resolved

    def sync_work(self, work_id: str) -> Dict[str, Any]:
        """将单部作品及其所有正文章节同步到本地目录"""
        work = memory_manager.get_work(work_id)
        if not work:
            raise ValueError(f"作品 {work_id} 不存在")

        settings = self.get_sync_settings()
        root_dir = self._ensure_sync_dir(settings["sync_dir"])
        ext = settings["file_format"]

        works_manifest_path = os.path.join(root_dir, MANIFEST_WORKS_FILE)
        works_manifest: Dict[str, str] = self._read_json_file(works_manifest_path, {})

        folder_name = self.sanitize_name(work["title"], fallback=f"作品_{work_id[:8]}")
        # 避免不同作品同名冲突，若已被另一 work_id 占用则附带短 ID
        for wid, wfolder in works_manifest.items():
            if wid != work_id and wfolder == folder_name:
                folder_name = f"{folder_name}_{work_id[:6]}"
                break

        old_folder_name = works_manifest.get(work_id)
        work_dir = os.path.join(root_dir, folder_name)

        # 若作品重命名，迁移旧目录名
        if old_folder_name and old_folder_name != folder_name:
            old_dir = os.path.join(root_dir, old_folder_name)
            if os.path.isdir(old_dir) and not os.path.exists(work_dir):
                os.rename(old_dir, work_dir)

        os.makedirs(work_dir, exist_ok=True)
        works_manifest[work_id] = folder_name
        self._write_json_file(works_manifest_path, works_manifest)

        written_files: List[str] = []

        # 1. 写入作品设定文件
        meta_filename = f"00_作品设定与大纲.{ext}"
        meta_path = os.path.join(work_dir, meta_filename)
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(self._format_work_meta(work, ext))
        written_files.append(meta_path)

        # 如果切换了格式 (.md <-> .txt)，清理旧格式的 00 文件
        other_ext = "txt" if ext == "md" else "md"
        stale_meta = os.path.join(work_dir, f"00_作品设定与大纲.{other_ext}")
        if os.path.isfile(stale_meta):
            os.remove(stale_meta)

        # 2. 写入所有正文章节，并使用清单管理已删除/重命名的旧章节文件
        chap_manifest_path = os.path.join(work_dir, MANIFEST_CHAPTERS_FILE)
        old_chap_manifest: Dict[str, str] = self._read_json_file(chap_manifest_path, {})
        new_chap_manifest: Dict[str, str] = {}

        chapters = memory_manager.list_chapters(work_id=work_id)
        used_filenames = {meta_filename}

        for idx, ch in enumerate(chapters, start=1):
            safe_title = self.sanitize_name(ch["title"], fallback=f"第{idx}章")
            base_name = f"{idx:02d}_{safe_title}"
            filename = f"{base_name}.{ext}"
            if filename in used_filenames:
                filename = f"{base_name}_{ch['id'][:6]}.{ext}"
            used_filenames.add(filename)

            file_path = os.path.join(work_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._format_chapter_content(ch, ext))

            new_chap_manifest[ch["id"]] = filename
            written_files.append(file_path)

        # 删除已经不在当前章节列表或已改名的旧同步文件
        active_filenames = set(new_chap_manifest.values())
        for old_fname in old_chap_manifest.values():
            if old_fname not in active_filenames:
                old_fpath = os.path.join(work_dir, old_fname)
                if os.path.isfile(old_fpath):
                    try:
                        os.remove(old_fpath)
                    except OSError:
                        pass

        self._write_json_file(chap_manifest_path, new_chap_manifest)

        return {
            "work_id": work_id,
            "work_title": work["title"],
            "work_dir": work_dir,
            "synced_chapters": len(chapters),
            "files": written_files,
        }

    def sync_all(self) -> Dict[str, Any]:
        """将全部作品与章节同步到本地目录"""
        settings = self.get_sync_settings()
        root_dir = self._ensure_sync_dir(settings["sync_dir"])

        works = memory_manager.list_works()
        active_work_ids = {w["id"] for w in works}

        # 清理已被删除作品的同步记录目录（仅清理清单追踪且无额外文件的文件夹）
        works_manifest_path = os.path.join(root_dir, MANIFEST_WORKS_FILE)
        works_manifest: Dict[str, str] = self._read_json_file(works_manifest_path, {})
        for old_wid, old_folder in list(works_manifest.items()):
            if old_wid not in active_work_ids:
                self._cleanup_removed_work_dir(os.path.join(root_dir, old_folder))
                works_manifest.pop(old_wid, None)
        self._write_json_file(works_manifest_path, works_manifest)

        details: List[Dict[str, Any]] = []
        total_chapters = 0
        for w in works:
            res = self.sync_work(w["id"])
            details.append(res)
            total_chapters += res["synced_chapters"]

        return {
            "sync_dir": root_dir,
            "file_format": settings["file_format"],
            "synced_works": len(works),
            "synced_chapters": total_chapters,
            "details": details,
        }

    def _cleanup_removed_work_dir(self, work_dir: str):
        """安全移除被删除作品的同步文件（仅删除同步生成的文件）"""
        if not os.path.isdir(work_dir):
            return
        chap_manifest_path = os.path.join(work_dir, MANIFEST_CHAPTERS_FILE)
        chap_manifest = self._read_json_file(chap_manifest_path, {})
        for fname in chap_manifest.values():
            fpath = os.path.join(work_dir, fname)
            if os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass
        for meta_name in ("00_作品设定与大纲.md", "00_作品设定与大纲.txt", MANIFEST_CHAPTERS_FILE):
            mpath = os.path.join(work_dir, meta_name)
            if os.path.isfile(mpath):
                try:
                    os.remove(mpath)
                except OSError:
                    pass
        try:
            if not os.listdir(work_dir):
                os.rmdir(work_dir)
        except OSError:
            pass

    def auto_sync_work_if_enabled(self, work_id: str):
        """若开启自动同步，则将作品最新内容实时写入本地目录"""
        try:
            settings = self.get_sync_settings()
            if settings["auto_sync"] and settings["sync_dir"]:
                self.sync_work(work_id)
        except Exception as e:
            print(f"[LocalSync] 自动同步作品 {work_id} 失败: {e}")

    def auto_sync_delete_work_if_enabled(self, work_id: str):
        """若开启自动同步，作品删除时清理对应同步文件夹"""
        try:
            settings = self.get_sync_settings()
            if not (settings["auto_sync"] and settings["sync_dir"]):
                return
            root_dir = settings["sync_dir"]
            works_manifest_path = os.path.join(root_dir, MANIFEST_WORKS_FILE)
            works_manifest: Dict[str, str] = self._read_json_file(works_manifest_path, {})
            folder_name = works_manifest.pop(work_id, None)
            if folder_name:
                self._cleanup_removed_work_dir(os.path.join(root_dir, folder_name))
                self._write_json_file(works_manifest_path, works_manifest)
        except Exception as e:
            print(f"[LocalSync] 清理删除作品 {work_id} 同步目录失败: {e}")


local_sync_manager = LocalSyncManager()

