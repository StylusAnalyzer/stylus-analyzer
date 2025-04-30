from tree_sitter import Language
import os

os.makedirs("build", exist_ok=True)

Language.build_library(
    'build/my-languages.so',
    [
        'tree-sitter-rust'
    ]
)

print("Successfully built build/my-languages.so with Rust grammar!")
