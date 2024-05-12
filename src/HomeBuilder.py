import os, subprocess
from src.ProjectConfig import config
from src.ConfigEntity import ConfigEntity
from src.FileLink import FileLink
from src.Script import Script


logger = logging.getLogger("Universal Home Builder")


class HomeBuilder:
    def __init__(self, config_entity: ConfigEntity):
        self.__config_entity = config_entity

        self.__link_pre_queue = []
        self.__link_post_queue = []
        self.__build_scripts_queue = []
        self.__user_scripts_queue = []

    def build(self):
        logger.info("Building home directory")
        self.__populate_queues()
        self.__link_pre_files()
        self.__run_build_scripts()
        self.__link_post_files()
        self.__link_user_scripts()

    def __populate_queues(self):
        logger.debug("Populating queues")
        config_entities_queue = [self.__config_entity]
        while len(config_entities_queue):
            config_entity = config_entities_queue.pop(0)

            for file_link in config_entity.file_links:
                if file_link.pre:
                    self.__link_pre_queue.append(file_link)
                if file_link.post:
                    self.__link_post_queue.append(file_link)

            for script in config_entity.scripts:
                if script.build:
                    self.__build_scripts_queue.append(script)
                if script.user:
                    self.__user_scripts_queue.append(script)

            config_entities_queue.extend(config_entity.imports)

        self.__build_scripts_queue.sort(key=lambda script: script.stage)

    def __link_pre_files(self):
        logger.info("Pre-linking files")
        for file_link in self.__link_pre_queue:
            self.link_file(file_link)

    def __run_build_scripts(self):
        logger.info("Running build scripts")
        for script in self.__build_scripts_queue:
            logger.info(f"Running build script: {script.name}")
            content = script.text if script.text is not None else script.source
            subprocess.run([content], check=True, shell=True)

    def __link_post_files(self):
        logger.info("Post-linking files")
        for file_link in self.__link_post_queue:
            self.link_file(file_link)

    def __link_user_scripts(self):
        logger.info("Linking user scripts")
        script_dir = config().get("user-scripts-bin", "~/.bin")
        logger.warning(f"Don't forget to add {script_dir} to your PATH")
        os.makedirs(os.path.expanduser(script_dir), mode=0o777, exist_ok=True)

        for script in self.__user_scripts_queue:
            logger.info(f"Linking user script: {script.name}")
            os.chmod(script.source, 0o755)
            destination = os.path.expanduser(
                os.path.join(script_dir, os.path.basename(script.source))
            )
            self.force_symlink(script.source, destination)

    @staticmethod
    def link_file(file_link: FileLink):
        logger.info(f"Linking {file_link.name}")
        self.force_symlink(file_link.source, file_link.destination)

    @staticmethod
    def force_symlink(source: str, destination: str):
        logger.debug(f"Symlink: {destination} -> {source}")
        try:
            if os.path.exists(destination):
                os.remove(destination)
            os.symlink(source, destination)
        except Exception as e:
            raise RuntimeError(
                f"Failed to create symlink: {destination} -> {source}"
            ) from e
