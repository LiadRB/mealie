import shutil
from enum import Enum

from fastapi import APIRouter, Depends, File, Form, HTTPException, status
from fastapi.datastructures import UploadFile
from mealie.db.database import db
from mealie.db.db_setup import generate_session
from mealie.routes.deps import get_current_user
from mealie.schema.recipe import Recipe, RecipeAsset
from slugify import slugify
from sqlalchemy.orm.session import Session
from starlette.responses import FileResponse

router = APIRouter(prefix="/api/recipes/media", tags=["Recipe Media"])


class ImageType(str, Enum):
    original = "original.webp"
    small = "min-original.webp"
    tiny = "tiny-original.webp"


@router.get("/{recipe_slug}/images/{file_name}")
async def get_recipe_img(recipe_slug: str, file_name: ImageType = ImageType.original):
    """Takes in a recipe slug, returns the static image. This route is proxied in the docker image
    and should not hit the API in production"""
    recipe_image = Recipe(slug=recipe_slug).image_dir.joinpath(file_name.value)

    if recipe_image:
        return FileResponse(recipe_image)
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


@router.get("/{recipe_slug}/assets/{file_name}")
async def get_recipe_asset(recipe_slug: str, file_name: str):
    """ Returns a recipe asset """
    file = Recipe(slug=recipe_slug).asset_dir.joinpath(file_name)

    try:
        return FileResponse(file)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


@router.post("/{recipe_slug}/assets", response_model=RecipeAsset)
def upload_recipe_asset(
    recipe_slug: str,
    name: str = Form(...),
    icon: str = Form(...),
    extension: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(generate_session),
    current_user=Depends(get_current_user),
):
    """ Upload a file to store as a recipe asset """
    file_name = slugify(name) + "." + extension
    asset_in = RecipeAsset(name=name, icon=icon, file_name=file_name)
    dest = Recipe(slug=recipe_slug).asset_dir.joinpath(file_name)

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if not dest.is_file():
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)

    recipe: Recipe = db.recipes.get(session, recipe_slug)
    recipe.assets.append(asset_in)
    db.recipes.update(session, recipe_slug, recipe.dict())
    return asset_in
