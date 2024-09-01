from langchain_community.document_loaders import UnstructuredFileIOLoader
from langchain_google_community import GoogleDriveLoader

file_id = "16qIHNp8L4RMHRC9Y8JzgvVA8KlDtmT81Yk7jRcZ09EU"
loader = GoogleDriveLoader(
    file_ids=[file_id],
    file_loader_cls=UnstructuredFileIOLoader,
    file_loader_kwargs={"mode": "elements"},
)

docs = loader.load()

docs[0]