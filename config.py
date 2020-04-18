# -*- coding: utf-8 -*-

# Configurations

logging.basicConfig(level=logging.INFO)

here = '/home/ayaka/Hub/Bench4BL/data/Wildfly/ELY'
bug_file_path = os.path.join(here, 'bugrepo/repository.xml')
repo_path = os.path.join(here, 'gitrepo')
embeddings_path = os.path.join(here, 'embeddings')

if not os.path.exists(embeddings_path):
	os.mkdir(embeddings_path)

chunk_size = 25  # For embeddings

# Constants

JAVA_KEYWORDS = ["abstract", "continue", "for", "new", "switch", "assert", "default", "goto", "package", "synchronized", "boolean", "do", "if", "private", "this", "break", "double", "implements", "protected", "throw", "byte", "else", "import", "public", "throws", "case", "enum", "instanceof", "return", "transient", "catch", "extends", "int", "short", "try", "char", "final", "interface", "static", "void", "class", "finally", "long", "strictfp", "volatile", "const", "float", "native", "super", "while", "org", "eclipse", "swt", "string", "main", "args", "null", "this", "extends", "true", "false"]
