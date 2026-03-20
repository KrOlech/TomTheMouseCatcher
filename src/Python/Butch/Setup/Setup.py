from src.Python.Setup.Setup import SetupUni



class Setup(SetupUni):

    def setUp(self):
        self.ensure_dir(self.logingApp.LogLocation)
