"""
创作数据层 Mixin (向前兼容适配层，领域逻辑已拆解至 app.stores.*)
"""
from app.stores.chapters import ChaptersStore
from app.stores.characters import CharactersStore
from app.stores.materials import MaterialsStore
from app.stores.prompts import PromptsStore
from app.stores.works import WorksStore


class CreativeStoreMixin(
    WorksStore,
    ChaptersStore,
    CharactersStore,
    MaterialsStore,
    PromptsStore,
):
    """向后兼容 Mixin，继承作品、章节、角色、素材与提示词 Store"""
    pass
