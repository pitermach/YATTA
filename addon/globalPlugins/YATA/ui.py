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
        self.targetLang = sHelper.addLabeledControl("Target Language (e.g. 'en', 'fr'):", wx.TextCtrl, value=conf.get("target_lang", "en"))
        
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
        self.ollamaPrompt = ollamaHelper.addLabeledControl("Ollama System Prompt:", wx.TextCtrl, value=conf.get("ollama_system_prompt", "You are an expert translator. Translate the given text to the target language."))
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
        conf["ollama_stream"] = self.ollamaStream.GetValue()
