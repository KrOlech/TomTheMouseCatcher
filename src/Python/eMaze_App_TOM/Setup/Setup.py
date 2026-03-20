from src.Python.Setup.Setup import SetupUni
from src.Python.eMaze_App_TOM.Settings import Settings


class Setup(SetupUni):

    def setUp(self):
        self.ensure_dir(Settings.dataLocation)
        self.ensure_dir(Settings.expectedLocation)
        self.ensure_dir(Settings.logLocation)
