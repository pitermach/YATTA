import wx
import gui
from gui.settingsDialogs import SettingsPanel
import config

class YATASettingsPanel(SettingsPanel):
    title = "YATA"
    
    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        self.serviceList = ["google", "bing", "deepl", "ollama", "openai", "gemini"]
        self.serviceNames = ["Google Translate (Free)", "Bing Translate (Free)", "DeepL", "Ollama", "OpenAI", "Google Gemini"]
        
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
        
        # LLM settings
        self.llmPanel = wx.Panel(self)
        llmSizer = wx.BoxSizer(wx.VERTICAL)
        llmHelper = gui.guiHelper.BoxSizerHelper(self.llmPanel, sizer=llmSizer)
        
        self.llmKey = llmHelper.addLabeledControl("API Key:", wx.TextCtrl, value="")
        self.llmAddress = llmHelper.addLabeledControl("Address / Base URL:", wx.TextCtrl, value="")
        self.llmModel = llmHelper.addLabeledControl("Model:", wx.TextCtrl, value="")
        self.btnSelectModel = wx.Button(self.llmPanel, label="Select Model...")
        self.btnSelectModel.Bind(wx.EVT_BUTTON, self.onSelectModel)
        llmHelper.addItem(self.btnSelectModel)
        
        self.llmPrompt = llmHelper.addLabeledControl("System Prompt:", wx.TextCtrl, style=wx.TE_MULTILINE, value="")
        self.llmUserPrompt = llmHelper.addLabeledControl("User Prompt:", wx.TextCtrl, style=wx.TE_MULTILINE, value="")
        self.btnLoadDefaultPrompt = wx.Button(self.llmPanel, label="Load Default Prompts")
        self.btnLoadDefaultPrompt.Bind(wx.EVT_BUTTON, self.onLoadDefaultPrompt)
        llmHelper.addItem(self.btnLoadDefaultPrompt)
        
        self.llmStream = llmHelper.addItem(wx.CheckBox(self.llmPanel, label="Stream responses"))
        self.llmPanel.SetSizer(llmSizer)
        sHelper.addItem(self.llmPanel)
        
        self.saveCache = sHelper.addItem(wx.CheckBox(self, label="Save cache to disk on exit"))
        self.saveCache.SetValue(conf.get("save_cache", True))
        
        self._current_service = current_service
        self._loadLLMConfig(self._current_service)
        
        self.updateVisibility()

    def onServiceChange(self, evt):
        self._saveLLMConfig(self._current_service)
        self._current_service = self.serviceList[self.serviceChoice.GetSelection()]
        self._loadLLMConfig(self._current_service)
        self.updateVisibility()
        
    def _saveLLMConfig(self, service):
        if service not in ("ollama", "openai", "gemini"): return
        conf = config.conf["YATA"]
        if service != "ollama": conf[f"{service}_key"] = self.llmKey.GetValue()
        if service in ("ollama", "openai"): conf[f"{service}_address"] = self.llmAddress.GetValue()
        conf[f"{service}_model"] = self.llmModel.GetValue()
        conf[f"{service}_system_prompt"] = self.llmPrompt.GetValue()
        conf[f"{service}_user_prompt"] = self.llmUserPrompt.GetValue()
        conf[f"{service}_stream"] = self.llmStream.GetValue()

    def _loadLLMConfig(self, service):
        if service not in ("ollama", "openai", "gemini"): return
        conf = config.conf["YATA"]
        self.llmKey.SetValue(conf.get(f"{service}_key", ""))
        self.llmAddress.SetValue(conf.get(f"{service}_address", ""))
        self.llmModel.SetValue(conf.get(f"{service}_model", ""))
        self.llmPrompt.SetValue(conf.get(f"{service}_system_prompt", ""))
        self.llmUserPrompt.SetValue(conf.get(f"{service}_user_prompt", ""))
        self.llmStream.SetValue(conf.get(f"{service}_stream", True))
        
    def updateVisibility(self):
        sel = self.serviceList[self.serviceChoice.GetSelection()]
        if sel == "deepl":
            self.deeplPanel.Show()
            self.llmPanel.Hide()
        elif sel in ("ollama", "openai", "gemini"):
            self.deeplPanel.Hide()
            self.llmPanel.Show()
            self.llmKey.Enable(sel != "ollama")
            self.llmAddress.Enable(sel != "gemini")
        else:
            self.deeplPanel.Hide()
            self.llmPanel.Hide()
        self.Layout()

    def onSave(self):
        conf = config.conf["YATA"]
        conf["service"] = self.serviceList[self.serviceChoice.GetSelection()]
        conf["source_lang"] = self.sourceLang.GetValue()
        conf["target_lang"] = self.targetLang.GetValue()
        conf["deepl_key"] = self.deeplKey.GetValue()
        conf["save_cache"] = self.saveCache.GetValue()
        self._saveLLMConfig(self._current_service)

    def onSelectLanguage(self, txtCtrl):
        import core
        sel = self.serviceList[self.serviceChoice.GetSelection()]
        
        conf_copy = config.conf["YATA"].copy()
        conf_copy["deepl_key"] = self.deeplKey.GetValue()
        self._saveLLMConfig(self._current_service)
        
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
        elif sel == "openai":
            from .services.openai import OpenAITranslate
            engine = OpenAITranslate(conf_copy)
        elif sel == "gemini":
            from .services.gemini import GeminiTranslate
            engine = GeminiTranslate(conf_copy)
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
        sel = self._current_service
        models = []
        try:
            if sel == "ollama":
                address = self.llmAddress.GetValue().rstrip("/")
                url = f"{address}/api/tags"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as response:
                    res = json.loads(response.read().decode('utf-8'))
                    models = [m['name'] for m in res.get('models', [])]
            elif sel == "openai":
                key = self.llmKey.GetValue().strip()
                address = self.llmAddress.GetValue().rstrip("/")
                url = f"{address}/models"
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    res = json.loads(response.read().decode('utf-8'))
                    models = [m['id'] for m in res.get('data', [])]
            elif sel == "gemini":
                key = self.llmKey.GetValue().strip()
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as response:
                    res = json.loads(response.read().decode('utf-8'))
                    models = [m['name'].split('/')[-1] for m in res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        except Exception as e:
            import ui
            ui.message(f"Failed to fetch models: {e}")
            return
            
        if not models:
            import ui
            ui.message("No models found.")
            return
            
        dlg = wx.SingleChoiceDialog(self, "Select Model:", f"{sel.capitalize()} Models", models)
        if dlg.ShowModal() == wx.ID_OK:
            self.llmModel.SetValue(dlg.GetStringSelection())
        dlg.Destroy()

    def onLoadDefaultPrompt(self, evt):
        import os
        import json
        model = self.llmModel.GetValue()
        addon_dir = os.path.dirname(__file__)
        prompts_file = os.path.join(addon_dir, "prompts.json")
        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts = json.load(f)
                
            for k in prompts:
                if k.lower() in model.lower():
                    entry = prompts[k]
                    self.llmPrompt.SetValue(entry.get("system_prompt", ""))
                    self.llmUserPrompt.SetValue(entry.get("user_prompt", ""))
                    import ui
                    ui.message("Default prompt loaded.")
                    return
                    
            import ui
            ui.message(f"No default prompt found for model: {model}")
        except Exception as e:
            import ui
            ui.message(f"Failed to load prompts: {e}")
