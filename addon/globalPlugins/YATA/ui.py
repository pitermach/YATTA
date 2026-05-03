import wx
import gui
from gui.settingsDialogs import SettingsPanel
import config

class YATASettingsPanel(SettingsPanel):
    title = "YATA"
    
    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        self.serviceList = ["google", "bing", "deepl", "ollama"]
        self.serviceNames = ["Google Translate (Free)", "Bing Translate (Free)", "DeepL", "Ollama"]
        
        conf = config.conf["YATA"]
        
        # Service Selection
        self.serviceChoice = sHelper.addLabeledControl("Translation Service:", wx.Choice, choices=self.serviceNames)
        current_service = conf.get("service", "google")
        try:
            self.serviceChoice.SetSelection(self.serviceList.index(current_service))
        except ValueError:
            self.serviceChoice.SetSelection(0)
            
        self.serviceChoice.Bind(wx.EVT_CHOICE, self.onServiceChange)
        
        # Languages
        self.sourceLang = sHelper.addLabeledControl("Source Language (e.g. 'auto', 'es'):", wx.TextCtrl, value=conf.get("source_lang", "auto"))
        self.btnSelectSource = wx.Button(self, label="Select Source Language...")
        self.btnSelectSource.Bind(wx.EVT_BUTTON, lambda e: self.onSelectLanguage(self.sourceLang))
        sHelper.addItem(self.btnSelectSource)
        
        self.targetLang = sHelper.addLabeledControl("Target Language (e.g. 'en', 'fr'):", wx.TextCtrl, value=conf.get("target_lang", "en"))
        self.btnSelectTarget = wx.Button(self, label="Select Target Language...")
        self.btnSelectTarget.Bind(wx.EVT_BUTTON, lambda e: self.onSelectLanguage(self.targetLang))
        sHelper.addItem(self.btnSelectTarget)
        
        # DeepL settings
        self.deeplPanel = wx.Panel(self)
        deeplSizer = wx.BoxSizer(wx.VERTICAL)
        deeplHelper = gui.guiHelper.BoxSizerHelper(self.deeplPanel, sizer=deeplSizer)
        self.deeplKey = deeplHelper.addLabeledControl("DeepL API Key:", wx.TextCtrl, value=conf.get("deepl_key", ""))
        self.deeplPanel.SetSizer(deeplSizer)
        sHelper.addItem(self.deeplPanel)
        
        # Ollama settings
        self.ollamaPanel = wx.Panel(self)
        ollamaSizer = wx.BoxSizer(wx.VERTICAL)
        ollamaHelper = gui.guiHelper.BoxSizerHelper(self.ollamaPanel, sizer=ollamaSizer)
        self.ollamaAddress = ollamaHelper.addLabeledControl("Ollama Address:", wx.TextCtrl, value=conf.get("ollama_address", "http://localhost:11434"))
        
        self.ollamaModel = ollamaHelper.addLabeledControl("Ollama Model:", wx.TextCtrl, value=conf.get("ollama_model", "gemma:2b"))
        self.btnSelectModel = wx.Button(self.ollamaPanel, label="Select Model...")
        self.btnSelectModel.Bind(wx.EVT_BUTTON, self.onSelectModel)
        ollamaHelper.addItem(self.btnSelectModel)
        
        self.ollamaPrompt = ollamaHelper.addLabeledControl("Ollama System Prompt:", wx.TextCtrl, style=wx.TE_MULTILINE, value=conf.get("ollama_system_prompt", "You are an expert translator. Translate the given text to the target language."))
        self.ollamaUserPrompt = ollamaHelper.addLabeledControl("Ollama User Prompt:", wx.TextCtrl, style=wx.TE_MULTILINE, value=conf.get("ollama_user_prompt", "{TEXT}"))
        self.btnLoadDefaultPrompt = wx.Button(self.ollamaPanel, label="Load Default Prompts")
        self.btnLoadDefaultPrompt.Bind(wx.EVT_BUTTON, self.onLoadDefaultPrompt)
        ollamaHelper.addItem(self.btnLoadDefaultPrompt)
        
        self.ollamaStream = ollamaHelper.addItem(wx.CheckBox(self.ollamaPanel, label="Stream responses"))
        self.ollamaStream.SetValue(conf.get("ollama_stream", True))
        self.ollamaPanel.SetSizer(ollamaSizer)
        sHelper.addItem(self.ollamaPanel)
        
        self.updateVisibility()

    def onServiceChange(self, evt):
        self.updateVisibility()
        
    def updateVisibility(self):
        sel = self.serviceList[self.serviceChoice.GetSelection()]
        if sel == "deepl":
            self.deeplPanel.Show()
            self.ollamaPanel.Hide()
        elif sel == "ollama":
            self.deeplPanel.Hide()
            self.ollamaPanel.Show()
        else:
            self.deeplPanel.Hide()
            self.ollamaPanel.Hide()
        self.Layout()

    def onSave(self):
        conf = config.conf["YATA"]
        conf["service"] = self.serviceList[self.serviceChoice.GetSelection()]
        conf["source_lang"] = self.sourceLang.GetValue()
        conf["target_lang"] = self.targetLang.GetValue()
        conf["deepl_key"] = self.deeplKey.GetValue()
        conf["ollama_address"] = self.ollamaAddress.GetValue()
        conf["ollama_model"] = self.ollamaModel.GetValue()
        conf["ollama_system_prompt"] = self.ollamaPrompt.GetValue()
        conf["ollama_user_prompt"] = self.ollamaUserPrompt.GetValue()
        conf["ollama_stream"] = self.ollamaStream.GetValue()

    def onSelectLanguage(self, txtCtrl):
        import core
        sel = self.serviceList[self.serviceChoice.GetSelection()]
        
        conf_copy = config.conf["YATA"].copy()
        conf_copy["deepl_key"] = self.deeplKey.GetValue()
        conf_copy["ollama_model"] = self.ollamaModel.GetValue()
        
        engine = None
        if sel == "bing":
            from .services.bing import BingTranslate
            engine = BingTranslate(conf_copy)
        elif sel == "deepl":
            from .services.deepl import DeepLTranslate
            engine = DeepLTranslate(conf_copy)
        elif sel == "ollama":
            from .services.ollama import OllamaTranslate
            engine = OllamaTranslate(conf_copy)
        else:
            from .services.google import GoogleTranslate
            engine = GoogleTranslate(conf_copy)
            
        langs = engine.get_supported_languages()
        if not langs:
            import ui
            ui.message("No languages found or failed to fetch.")
            return
            
        choices = [f"{v} ({k})" for k, v in langs.items()]
        choices.sort()
        if txtCtrl == self.sourceLang:
            choices.insert(0, "Auto-detect (auto)")
            
        dlg = wx.SingleChoiceDialog(self, "Select Language:", "Language", choices)
        if dlg.ShowModal() == wx.ID_OK:
            sel_str = dlg.GetStringSelection()
            code = sel_str.split("(")[-1].split(")")[0]
            txtCtrl.SetValue(code)
        dlg.Destroy()

    def onSelectModel(self, evt):
        import urllib.request
        import json
        address = self.ollamaAddress.GetValue().rstrip("/")
        url = f"{address}/api/tags"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                res = json.loads(response.read().decode('utf-8'))
                models = [m['name'] for m in res.get('models', [])]
        except Exception as e:
            import ui
            ui.message(f"Failed to fetch models: {e}")
            return
            
        if not models:
            import ui
            ui.message("No models found.")
            return
            
        dlg = wx.SingleChoiceDialog(self, "Select Model:", "Ollama Models", models)
        if dlg.ShowModal() == wx.ID_OK:
            self.ollamaModel.SetValue(dlg.GetStringSelection())
        dlg.Destroy()

    def onLoadDefaultPrompt(self, evt):
        import os
        import json
        model = self.ollamaModel.GetValue()
        addon_dir = os.path.dirname(__file__)
        prompts_file = os.path.join(addon_dir, "prompts.json")
        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts = json.load(f)
                
            for k in prompts:
                if k.lower() in model.lower():
                    entry = prompts[k]
                    self.ollamaPrompt.SetValue(entry.get("system_prompt", ""))
                    self.ollamaUserPrompt.SetValue(entry.get("user_prompt", ""))
                    import ui
                    ui.message("Default prompt loaded.")
                    return
                    
            import ui
            ui.message(f"No default prompt found for model: {model}")
        except Exception as e:
            import ui
            ui.message(f"Failed to load prompts: {e}")
