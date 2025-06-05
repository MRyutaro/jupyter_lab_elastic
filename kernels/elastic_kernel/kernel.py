import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from elastic.elastic_notebook import ElasticNotebook
from ipykernel.ipkernel import IPythonKernel

# 環境変数ROOT_DIRを取得
ROOT_DIR = os.getenv("ROOT_DIR")
if ROOT_DIR is None:
    raise ValueError("ROOT_DIR is not set.")

LOG_FILE_PATH = f"{ROOT_DIR}/kernels/elastic_kernel/logs/elastic_kernel.log"
DEFAULT_CHECKPOINT_FILE_PATH = f"{ROOT_DIR}/kernels/elastic_kernel/checkpoints/default.pickle"

# ログディレクトリが存在しない場合は作成
log_dir = os.path.dirname(LOG_FILE_PATH)
os.makedirs(log_dir, exist_ok=True)

# ロガーの設定
logger = logging.getLogger("ElasticKernelLogger")
logger.setLevel(logging.DEBUG)  # ログレベルを設定
formatter = logging.Formatter(
    "[%(asctime)s ElasticKernelLogger %(levelname)s] %(message)s"
)

# コンソールハンドラー
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ローテーティングファイルハンドラー
rotating_file_handler = RotatingFileHandler(
    LOG_FILE_PATH,
    maxBytes=5 * 1024 * 1024,
    backupCount=5,  # 5MBのログサイズでローテーション、5世代保存
)
rotating_file_handler.setLevel(logging.DEBUG)
rotating_file_handler.setFormatter(formatter)
logger.addHandler(rotating_file_handler)


class ElasticKernel(IPythonKernel):
    implementation = "elastic_kernel"
    implementation_version = "1.0"
    language = "python"
    language_version = "3.x"
    language_info = {
        "name": "python",
        "mimetype": "text/x-python",
        "file_extension": ".py",
    }
    banner = "Elastic Python Kernel with Hooks"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("=====================================")
        logger.info("Initializing ElasticKernel")
        logger.info("=====================================")

        # コマンドライン引数を取得
        logger.debug(f"Kernel Args: {sys.argv}")
        logger.debug(f"kwargs: {kwargs}")
        logger.debug(f"self.shell: {self.shell}")

        try:
            # セッション情報からノートブックのパスを取得
            session_path = self.shell.user_ns.get("__session__")
            logger.info(f"Session path: {session_path}")

            if session_path:
                # ノートブックのファイル名を取得（拡張子を除く）
                notebook_name = Path(session_path).stem

                # チェックポイントファイルのパスを設定
                checkpoint_dir = (
                    Path(ROOT_DIR) / "kernels" / "elastic_kernel" / "checkpoints"
                )
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                self.checkpoint_file_name = str(
                    checkpoint_dir / f"{notebook_name}.pickle"
                )

                logger.info(f"Using checkpoint file: {self.checkpoint_file_name}")
            else:
                # セッション情報が取得できない場合はデフォルトのパスを使用
                self.checkpoint_file_name = DEFAULT_CHECKPOINT_FILE_PATH
                logger.info(
                    f"No session path found. Using default checkpoint file: {self.checkpoint_file_name}"
                )
        except Exception as e:
            logger.error(f"Error setting checkpoint file name: {e}")
            # フォールバック：デフォルトのチェックポイントファイル名を使用
            self.checkpoint_file_name = DEFAULT_CHECKPOINT_FILE_PATH
            logger.info(
                f"Falling back to default checkpoint file: {self.checkpoint_file_name}"
            )

        # ElasticNotebookをロードする
        try:
            self.elastic_notebook = ElasticNotebook(self.shell)
            logger.info("ElasticNotebook successfully loaded.")
        except Exception as e:
            logger.error(f"Error loading ElasticNotebook: {e}")

        # チェックポイントをロードする
        logger.info(f"{self.shell.user_ns['__session__']=}")
        if os.path.exists(self.checkpoint_file_name):
            logger.info("Checkpoint file exists. Loading checkpoint.")
            try:
                self.elastic_notebook.load_checkpoint(self.checkpoint_file_name)
                logger.debug(
                    f"{self.elastic_notebook.dependency_graph.variable_snapshots=}"
                )
                logger.debug(f"{self.shell.user_ns=}")
                logger.info("Checkpoint successfully loaded.")
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
        else:
            logger.info("Checkpoint file does not exist. Skipping loading checkpoint.")

    def __del_from_user_ns_hidden(self):
        # %whoで表示されるようにするために復元した変数をself.shell.user_ns_hiddenから削除する
        logger.debug(f"Initial {self.shell.user_ns_hidden=}")

        variable_snapshots = set(
            self.elastic_notebook.dependency_graph.variable_snapshots
        )
        user_ns_hidden_keys = set(self.shell.user_ns_hidden.keys())

        # 削除対象の変数名を一括で取得
        variables_to_delete = variable_snapshots & user_ns_hidden_keys

        # 一括で削除
        for variable_name in variables_to_delete:
            logger.debug(f"Deleting {variable_name} from self.shell.user_ns_hidden")
            del self.shell.user_ns_hidden[variable_name]

        logger.debug(f"Final {self.shell.user_ns_hidden=}")

    def __skip_record(self, code):
        skip_magic_commands = ["!", "%", "%%"]
        is_magic_command = any(
            code.strip().startswith(magic) for magic in skip_magic_commands
        )
        if is_magic_command:
            return True

        # TODO: bashなどpythonコードではない場合はスキップする

        return False

    def do_execute(
        self, code, silent, store_history=True, user_expressions=None, allow_stdin=False
    ):
        logger.debug(f"Executing Code:\n{code}")
        result = super().do_execute(
            code, silent, store_history, user_expressions, allow_stdin
        )

        if not self.__skip_record(code):
            self.elastic_notebook.record_event(code)
            logger.debug("Recording event")
        else:
            logger.debug("Skipping record event")

        # TODO: ここで毎回呼ぶのは効率悪いのでは？
        self.__del_from_user_ns_hidden()

        return result

    def do_shutdown(self, restart):
        logger.debug("Shutting Down Kernel")
        self.elastic_notebook.checkpoint(self.checkpoint_file_name)
        return super().do_shutdown(restart)


if __name__ == "__main__":
    # from ipykernel.kernelapp import IPKernelApp
    # IPKernelApp.launch_instance(kernel_class=ElasticKernel)
    from ipykernel import kernelapp as app

    app.launch_new_instance(kernel_class=ElasticKernel)
