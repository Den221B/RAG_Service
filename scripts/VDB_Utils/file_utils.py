from pathlib import Path
import shutil
from tqdm import tqdm


def move_documents(source_dir: Path, target_dir: Path) -> None:
    """
    Move all PDF and DOCX files from source_dir to target_dir.

    Args:
        source_dir (Path): Directory to move documents from.
        target_dir (Path): Directory to move documents to.
    """
    files = list(source_dir.rglob("*.pdf")) + list(source_dir.rglob("*.docx"))
    if not files:
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    for file in tqdm(files, desc="📂 Moving documents"):
        shutil.move(str(file), str(target_dir / file.name))


def remove_duplicates(new_dir: Path, existing_dir: Path) -> None:
    """
    Remove files from new_dir that already exist (by name) in existing_dir.

    Args:
        new_dir (Path): Directory containing newly added files.
        existing_dir (Path): Directory with existing files.
    """
    new_files = list(new_dir.rglob("*.[pd][od][fcx]"))  # Matches *.pdf and *.docx
    existing_names = {f.name for f in existing_dir.rglob("*.[pd][od][fcx]")}

    removed_count = 0
    for file in new_files:
        if file.name in existing_names:
            file.unlink()
            removed_count += 1
            print(f"🗑️ Removed duplicate: {file.name}")

    if removed_count:
        print(f"✅ Total duplicates removed: {removed_count}")


def replace_documents(target_dir: Path, source_dir: Path) -> None:
    """
    Replace all documents in target_dir with those from source_dir.

    This function:
    - Deletes all content in target_dir.
    - Moves PDF and DOCX files from source_dir to target_dir.
    - Clears source_dir afterward.

    Args:
        target_dir (Path): Destination directory to receive new documents.
        source_dir (Path): Directory containing new documents to move.
    """
    print(f"🔁 Clearing target directory: {target_dir}")
    shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    move_documents(source_dir, target_dir)

    print(f"🧹 Clearing source directory: {source_dir}")
    shutil.rmtree(source_dir, ignore_errors=True)
    source_dir.mkdir(parents=True, exist_ok=True)
