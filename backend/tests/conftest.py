"""Keep test source files isolated from the user's real content-addressed assets."""
import os,tempfile
os.environ.setdefault('FOOD_DATA_DIR',tempfile.mkdtemp(prefix='food-agent-test-assets-'))
