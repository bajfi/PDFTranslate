import copy
import json
import os
from pathlib import Path
from threading import RLock  # 改成 RLock


class ConfigManager:
    _instance = None
    _lock = RLock()  # use RLock for reentrant locking

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        # Check if instance exists, if not create it
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Avoid re-initialization
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._config_path = Path.home() / ".config" / "PDFMathTranslate" / "config.json"
        self._config_data = {}

        # 这里不要再加锁，因为外层可能已经加了锁 (get_instance), RLock也无妨
        self._ensure_config_exists()

    def _ensure_config_exists(self, isInit=True):
        """Ensure config.json exists."""
        if not self._config_path.exists():
            if isInit:
                self._config_path.parent.mkdir(parents=True, exist_ok=True)
                self._config_data = {}  # 默认配置内容
                self._save_config()
            else:
                raise ValueError(f"config file {self._config_path} not found!")
        else:
            self._load_config()

    def _load_config(self):
        """Load config.json"""
        with self._lock:  # 加锁确保线程安全
            with self._config_path.open("r", encoding="utf-8") as f:
                self._config_data = json.load(f)

    def _save_config(self):
        """Save config.json"""
        with self._lock:  # 加锁确保线程安全
            # 移除循环引用并写入
            cleaned_data = self._remove_circular_references(self._config_data)
            with self._config_path.open("w", encoding="utf-8") as f:
                json.dump(cleaned_data, f, indent=4, ensure_ascii=False)

    def _remove_circular_references(self, obj, seen=None):
        """Remove circular references from config data."""
        if seen is None:
            seen = set()
        obj_id = id(obj)
        if obj_id in seen:
            return None  # 遇到已处理过的对象，视为循环引用
        seen.add(obj_id)

        if isinstance(obj, dict):
            return {
                k: self._remove_circular_references(v, seen) for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self._remove_circular_references(i, seen) for i in obj]
        return obj

    @classmethod
    def custome_config(cls, file_path):
        """use custom config file"""
        custom_path = Path(file_path)
        if not custom_path.exists():
            raise ValueError(f"Config file {custom_path} not found!")
        # 加锁
        with cls._lock:
            instance = cls()
            instance._config_path = custom_path
            # 此处传 isInit=False，若不存在则报错；若存在则正常 _load_config()
            instance._ensure_config_exists(isInit=False)
            cls._instance = instance

    @classmethod
    def get(cls, key, default=None):
        """get config value"""
        instance = cls.get_instance()
        # 读取时，加锁或不加锁都行。但为了统一，我们在修改配置前后都要加锁。
        # get 只要最终需要保存，则会加锁 -> _save_config()
        if key in instance._config_data:
            return instance._config_data[key]

        # 若环境变量中存在该 key，则使用环境变量并写回 config
        if key in os.environ:
            value = os.environ[key]
            instance._config_data[key] = value
            instance._save_config()
            return value

        # 若 default 不为 None，则设置并保存
        if default is not None:
            instance._config_data[key] = default
            instance._save_config()
            return default

        # 找不到则抛出异常
        # raise KeyError(f"{key} is not found in config file or environment variables.")
        return default

    @classmethod
    def set(cls, key, value):
        """set config value"""
        instance = cls.get_instance()
        with instance._lock:
            instance._config_data[key] = value
            instance._save_config()

    @classmethod
    def get_translator_by_name(cls, name):
        """get env by translater name"""
        instance = cls.get_instance()
        translators = instance._config_data.get("translators", [])
        for translator in translators:
            if translator.get("name") == name:
                return translator["envs"]
        return None

    @classmethod
    def set_translator_by_name(cls, name, new_translator_envs):
        """set/update translator envs by name"""
        instance = cls.get_instance()
        with instance._lock:
            translators = instance._config_data.get("translators", [])
            for translator in translators:
                if translator.get("name") == name:
                    translator["envs"] = copy.deepcopy(new_translator_envs)
                    instance._save_config()
                    return
            translators.append(
                {"name": name, "envs": copy.deepcopy(new_translator_envs)}
            )
            instance._config_data["translators"] = translators
            instance._save_config()

    @classmethod
    def get_env_by_translatername(cls, translater_name, name, default=None):
        """get env by translater name"""
        instance = cls.get_instance()
        translators = instance._config_data.get("translators", [])
        for translator in translators:
            if translator.get("name") == translater_name.name:
                if translator["envs"][name]:
                    return translator["envs"][name]
                else:
                    with instance._lock:
                        translator["envs"][name] = default
                        instance._save_config()
                        return default

        with instance._lock:
            translators = instance._config_data.get("translators", [])
            for translator in translators:
                if translator.get("name") == translater_name.name:
                    translator["envs"][name] = default
                    instance._save_config()
                    return default
            translators.append(
                {
                    "name": translater_name.name,
                    "envs": copy.deepcopy(translater_name.envs),
                }
            )
            instance._config_data["translators"] = translators
            instance._save_config()
            return default

    @classmethod
    def delete(cls, key):
        """delete config value and save"""
        instance = cls.get_instance()
        with instance._lock:
            if key in instance._config_data:
                del instance._config_data[key]
                instance._save_config()

    @classmethod
    def clear(cls):
        """delete config value and save"""
        instance = cls.get_instance()
        with instance._lock:
            instance._config_data = {}
            instance._save_config()

    @classmethod
    def all(cls):
        """return all config items"""
        instance = cls.get_instance()
        # 这里只做读取操作，一般可不加锁。不过为了保险也可以加锁。
        return instance._config_data

    @classmethod
    def remove(cls):
        instance = cls.get_instance()
        with instance._lock:
            os.remove(instance._config_path)
