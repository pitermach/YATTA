import wx
import gui
import config
import addonHandler
from gui.settingsDialogs import SettingsPanel
import addonHandler
import os
import re
import string
import urllib.request
import json
import core
import ui as nvda_ui
import configobj
import globalVars
import tones
from . import cache
from .services.google import GoogleTranslate
from .services.bing import BingTranslate
from .services.deepl import DeepLTranslate
from .services.ollama import OllamaTranslate
from .services.openai import OpenAITranslate
from .services.gemini import GeminiTranslate

addonHandler.initTranslation()


class LanguageSelectionDialog(wx.Dialog):
    def __init__(self, parent, title, choices, langs_dict, service):
        super().__init__(parent, title=title)
        self.langs_dict = langs_dict
        self.service = service
        self.selected_code = None
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        label = wx.StaticText(self, label=_("Language:"))
        mainSizer.Add(label, 0, wx.ALL, 5)
        
        self.combo = wx.ComboBox(self, choices=choices, style=wx.CB_DROPDOWN)
        mainSizer.Add(self.combo, 0, wx.EXPAND | wx.ALL, 5)
        
        btnSizer = wx.StdDialogButtonSizer()
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.SetDefault()
        btnSizer.AddButton(btnOK)
        btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnSizer.AddButton(btnCancel)
        btnSizer.Realize()
        
        mainSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, 5)
        
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        
    def onOK(self, evt):
        val = self.combo.GetValue().strip()
        if not val:
            evt.Skip()
            return
            
        code = val
        if "(" in val and ")" in val:
            code = val.split("(")[-1].split(")")[0].strip()
            
        for k, v in self.langs_dict.items():
            if v.lower() == val.lower():
                code = k
                break
                
        if self.service not in ("ollama", "openai", "gemini"):
            if code.lower() == "auto":
                pass
            elif code not in self.langs_dict:
                gui.messageBox(_("Invalid language selected. Please choose a supported language from the list or enter a valid code."), _("Error"), style=wx.OK | wx.ICON_ERROR, parent=self)
                return
                
        self.selected_code = code
        self.EndModal(wx.ID_OK)

def select_language_helper(parent, current_code, service, conf_copy, is_source):
    engine = None
    if service == "bing":
        engine = BingTranslate(conf_copy)
    elif service == "deepl":
        engine = DeepLTranslate(conf_copy)
    elif service == "ollama":
        engine = OllamaTranslate(conf_copy)
    elif service == "openai":
        engine = OpenAITranslate(conf_copy)
    elif service == "gemini":
        engine = GeminiTranslate(conf_copy)
    else:
        engine = GoogleTranslate(conf_copy)
        
    langs = engine.get_supported_languages()
    if not langs:
        nvda_ui.message(_("No languages found or failed to fetch."))
        return None
        
    choices = [f"{v} ({k})" for k, v in langs.items()]
    choices.sort()
    if is_source:
        choices.insert(0, _("Auto-detect (auto)"))
        
    dlg = LanguageSelectionDialog(parent, _("Select Language:"), choices, langs, service)
    if current_code.lower() == "auto" and is_source:
        dlg.combo.SetValue(_("Auto-detect (auto)"))
    elif current_code in langs:
        dlg.combo.SetValue(f"{langs[current_code]} ({current_code})")
    else:
        dlg.combo.SetValue(current_code)
        
    res = dlg.ShowModal()
    code = dlg.selected_code if res == wx.ID_OK else None
    dlg.Destroy()
    return code

def load_default_prompt_helper(model, sysPromptCtrl, usrPromptCtrl):
    addon_dir = os.path.dirname(__file__)
    prompts_file = os.path.join(addon_dir, "prompts.json")
    try:
        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts = json.load(f)
            
        for k in prompts:
            if k.lower() in model.lower():
                entry = prompts[k]
                sysPromptCtrl.SetValue(entry.get("system_prompt", ""))
                usrPromptCtrl.SetValue(entry.get("user_prompt", ""))
                nvda_ui.message(_("Default prompt loaded."))
                return
                
        nvda_ui.message(_("No default prompt found for model: {model}").format(model=model))
    except Exception as e:
        nvda_ui.message(_("Failed to load prompts: {e}").format(e=e).format(e=e))

class YATAAppDialog(wx.Dialog):
    def __init__(self, parent, app_name):
        super().__init__(parent, title=_("YATA settings - {app_name}").format(app_name=app_name).format(app_name=app_name))
        self.app_name = app_name
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=mainSizer)
        
        settings_dir = os.path.join(globalVars.appArgs.configPath, "YATA", "settings")
        if not os.path.exists(settings_dir):
            try:
                os.makedirs(settings_dir)
            except Exception:
                pass
        self.filepath = os.path.join(settings_dir, f"{app_name}.ini")
        if os.path.exists(self.filepath):
            self.app_conf = configobj.ConfigObj(self.filepath)
        else:
            self.app_conf = configobj.ConfigObj()
            
        self.global_conf = config.conf["YATA"]
        self.service = self.global_conf.get("service", "google")
        
        def get_val(key, global_fallback):
            if key in self.app_conf:
                return self.app_conf[key]
            return self.global_conf.get(global_fallback, "")

        self.sourceLangCode = get_val("source_lang", "source_lang")
        self.btnSelectSource = wx.Button(self, label=_("&Source Language: {lang}").format(lang=self.sourceLangCode))
        self.btnSelectSource.Bind(wx.EVT_BUTTON, lambda e: self.onSelectLanguage(True))
        sHelper.addItem(self.btnSelectSource)
        
        self.targetLangCode = get_val("target_lang", "target_lang")
        self.btnSelectTarget = wx.Button(self, label=_("&Target Language: {lang}").format(lang=self.targetLangCode))
        self.btnSelectTarget.Bind(wx.EVT_BUTTON, lambda e: self.onSelectLanguage(False))
        sHelper.addItem(self.btnSelectTarget)
        
        # Prompts
        if self.service in ("ollama", "openai", "gemini"):
            sys_prompt_val = get_val("system_prompt", f"{self.service}_system_prompt")
            usr_prompt_val = get_val("user_prompt", f"{self.service}_user_prompt")
            
            self.sysPrompt = sHelper.addLabeledControl(_("System Prompt:"), wx.TextCtrl, style=wx.TE_MULTILINE, value=sys_prompt_val)
            self.usrPrompt = sHelper.addLabeledControl(_("User Prompt:"), wx.TextCtrl, style=wx.TE_MULTILINE, value=usr_prompt_val)
            
            self.btnLoadDefaultPrompt = wx.Button(self, label=_("Load Default Prompts"))
            self.btnLoadDefaultPrompt.Bind(wx.EVT_BUTTON, self.onLoadDefaultPrompt)
            sHelper.addItem(self.btnLoadDefaultPrompt)
        
        save_cache_val = self.app_conf.get("save_cache", str(self.global_conf.get("save_cache", True))).lower() == 'true'
        self.saveCache = sHelper.addItem(wx.CheckBox(self, label=_("Save cache to disk")))
        self.saveCache.SetValue(save_cache_val)
        
        auto_trans_val = self.app_conf.get("auto_translate", "False").lower() == 'true'
        self.autoTranslate = sHelper.addItem(wx.CheckBox(self, label=_("Enable automatic translation")))
        self.autoTranslate.SetValue(auto_trans_val)
        play_sound_val = self.app_conf.get("play_sound", str(self.global_conf.get("play_sound", True))).lower() == 'true'
        self.playSound = sHelper.addItem(wx.CheckBox(self, label=_("Play sound during longer operations")))
        self.playSound.SetValue(play_sound_val)

        
        sep_num_val = self.app_conf.get("separate_numbers", str(self.global_conf.get("separate_numbers", False))).lower() == 'true'
        self.separateNumbers = sHelper.addItem(wx.CheckBox(self, label=_("Separate numbers when translating")))
        self.separateNumbers.SetValue(sep_num_val)
        
        # Buttons
        btnSizer = wx.StdDialogButtonSizer()
        
        self.btnReset = wx.Button(self, label=_("Reset"))
        self.btnReset.Bind(wx.EVT_BUTTON, self.onReset)
        btnSizer.AddButton(self.btnReset)
        
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.SetDefault()
        btnSizer.AddButton(btnOK)
        
        btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnSizer.AddButton(btnCancel)
        btnSizer.Realize()
        
        sHelper.addItem(btnSizer)
        
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self.onCancel)
        
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        
    def onSelectLanguage(self, is_source):
        conf_copy = self.global_conf.copy()
        current = self.sourceLangCode if is_source else self.targetLangCode
        res = select_language_helper(self, current, self.service, conf_copy, is_source)
        if res is not None:
            if is_source:
                self.sourceLangCode = res
                self.btnSelectSource.SetLabel(_("&Source Language: {lang}").format(lang=res))
            else:
                self.targetLangCode = res
                self.btnSelectTarget.SetLabel(_("&Target Language: {lang}").format(lang=res))
        
    def onLoadDefaultPrompt(self, evt):
        model = self.global_conf.get(f"{self.service}_model", "")
        load_default_prompt_helper(model, self.sysPrompt, self.usrPrompt)
        
    def onReset(self, evt):
        if gui.messageBox(_("Are you sure you want to reset settings for this app?"), _("Confirm Reset"), style=wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
            self.Destroy()
            
    def onOK(self, evt):
        self.app_conf["source_lang"] = self.sourceLangCode
        self.app_conf["target_lang"] = self.targetLangCode
        if hasattr(self, "sysPrompt"):
            self.app_conf["system_prompt"] = self.sysPrompt.GetValue()
            self.app_conf["user_prompt"] = self.usrPrompt.GetValue()
        self.app_conf["save_cache"] = str(self.saveCache.GetValue())
        self.app_conf["auto_translate"] = str(self.autoTranslate.GetValue())
        self.app_conf["play_sound"] = str(self.playSound.GetValue())
        self.app_conf["separate_numbers"] = str(self.separateNumbers.GetValue())
        
        self.app_conf.filename = self.filepath
        self.app_conf.write()
        self.Destroy()
        
    def onCancel(self, evt):
        self.Destroy()

class YATASettingsPanel(SettingsPanel):
    title = "YATA"
    
    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        self.serviceList = ["google", "bing", "deepl", "ollama", "openai", "gemini"]
        self.serviceNames = ["Google Translate (Free)", "Bing Translate (Free)", "DeepL", "Ollama", "OpenAI", "Google Gemini"]
        
        conf = config.conf["YATA"]
        
        # Service Selection
        self.serviceChoice = sHelper.addLabeledControl(_("Translation Service:"), wx.Choice, choices=self.serviceNames)
        current_service = conf.get("service", "google")
        try:
            self.serviceChoice.SetSelection(self.serviceList.index(current_service))
        except ValueError:
            self.serviceChoice.SetSelection(0)
            
        self.serviceChoice.Bind(wx.EVT_CHOICE, self.onServiceChange)
        
        # Languages
        self.sourceLangCode = conf.get("source_lang", "auto")
        self.btnSelectSource = wx.Button(self, label=_("&Source Language: {lang}").format(lang=self.sourceLangCode))
        self.btnSelectSource.Bind(wx.EVT_BUTTON, lambda e: self.onSelectLanguage(True))
        sHelper.addItem(self.btnSelectSource)
        
        self.targetLangCode = conf.get("target_lang", "en")
        self.btnSelectTarget = wx.Button(self, label=_("&Target Language: {lang}").format(lang=self.targetLangCode))
        self.btnSelectTarget.Bind(wx.EVT_BUTTON, lambda e: self.onSelectLanguage(False))
        sHelper.addItem(self.btnSelectTarget)
        
        # DeepL settings
        self.deeplPanel = wx.Panel(self)
        deeplSizer = wx.BoxSizer(wx.VERTICAL)
        deeplHelper = gui.guiHelper.BoxSizerHelper(self.deeplPanel, sizer=deeplSizer)
        self.deeplKey = deeplHelper.addLabeledControl(_("DeepL API Key:"), wx.TextCtrl, value=conf.get("deepl_key", ""))
        self.deeplPanel.SetSizer(deeplSizer)
        sHelper.addItem(self.deeplPanel)
        
        # LLM settings
        self.llmPanel = wx.Panel(self)
        llmSizer = wx.BoxSizer(wx.VERTICAL)
        llmHelper = gui.guiHelper.BoxSizerHelper(self.llmPanel, sizer=llmSizer)
        
        self.llmKey = llmHelper.addLabeledControl(_("API Key:"), wx.TextCtrl, value="")
        self.llmAddress = llmHelper.addLabeledControl(_("Address / Base URL:"), wx.TextCtrl, value="")
        self.llmModel = llmHelper.addLabeledControl(_("Model:"), wx.TextCtrl, value="")
        self.btnSelectModel = wx.Button(self.llmPanel, label=_("Select Model..."))
        self.btnSelectModel.Bind(wx.EVT_BUTTON, self.onSelectModel)
        llmHelper.addItem(self.btnSelectModel)
        
        self.llmPrompt = llmHelper.addLabeledControl(_("System Prompt:"), wx.TextCtrl, style=wx.TE_MULTILINE, value="")
        self.llmUserPrompt = llmHelper.addLabeledControl(_("User Prompt:"), wx.TextCtrl, style=wx.TE_MULTILINE, value="")
        self.btnLoadDefaultPrompt = wx.Button(self.llmPanel, label=_("Load Default Prompts"))
        self.btnLoadDefaultPrompt.Bind(wx.EVT_BUTTON, self.onLoadDefaultPrompt)
        llmHelper.addItem(self.btnLoadDefaultPrompt)
        
        self.llmStream = llmHelper.addItem(wx.CheckBox(self.llmPanel, label=_("Stream responses")))
        self.llmPanel.SetSizer(llmSizer)
        sHelper.addItem(self.llmPanel)
        
        self.saveCache = sHelper.addItem(wx.CheckBox(self, label=_("Save cache to disk on exit")))
        self.saveCache.SetValue(conf.get("save_cache", True))
        
        self.separateNumbers = sHelper.addItem(wx.CheckBox(self, label=_("Separate numbers when translating")))
        self.separateNumbers.SetValue(conf.get("separate_numbers", False))
        
        self.autoSwap = sHelper.addItem(wx.CheckBox(self, label=_("Automatically Swap languages if text is already in Target language")))
        self.autoSwap.SetValue(conf.get("auto_swap", False))
        
        self.playSound = sHelper.addItem(wx.CheckBox(self, label=_("Play sound during longer operations")))
        play_sound_val = conf.get("play_sound", True)
        if isinstance(play_sound_val, str):
            play_sound_val = play_sound_val.lower() == 'true'
        self.playSound.SetValue(play_sound_val)
        
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
            
        supports_detection = sel in ("google", "bing", "deepl")
        if supports_detection and self.sourceLangCode != "auto":
            self.autoSwap.Enable()
        else:
            self.autoSwap.Disable()
            
        self.Layout()

    def onSave(self):
        conf = config.conf["YATA"]
        conf["service"] = self.serviceList[self.serviceChoice.GetSelection()]
        conf["source_lang"] = self.sourceLangCode
        conf["target_lang"] = self.targetLangCode
        conf["deepl_key"] = self.deeplKey.GetValue()
        conf["save_cache"] = self.saveCache.GetValue()
        conf["separate_numbers"] = self.separateNumbers.GetValue()
        conf["auto_swap"] = self.autoSwap.GetValue()
        conf["play_sound"] = self.playSound.GetValue()
        self._saveLLMConfig(self._current_service)

    def onSelectLanguage(self, is_source):
        sel = self.serviceList[self.serviceChoice.GetSelection()]
        conf_copy = config.conf["YATA"].copy()
        conf_copy["deepl_key"] = self.deeplKey.GetValue()
        self._saveLLMConfig(self._current_service)
        current = self.sourceLangCode if is_source else self.targetLangCode
        res = select_language_helper(self, current, sel, conf_copy, is_source)
        if res is not None:
            if is_source:
                self.sourceLangCode = res
                self.btnSelectSource.SetLabel(_("&Source Language: {lang}").format(lang=res))
            else:
                self.targetLangCode = res
                self.btnSelectTarget.SetLabel(_("&Target Language: {lang}").format(lang=res))
        self.updateVisibility()

    def onSelectModel(self, evt):
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
            ui.message(f_("Failed to fetch models: {e}").format(e=e))
            return
            
        if not models:
            ui.message("No models found.")
            return
            
        dlg = wx.SingleChoiceDialog(self, _("Select Model:"), f"{sel.capitalize()} Models", models)
        if dlg.ShowModal() == wx.ID_OK:
            self.llmModel.SetValue(dlg.GetStringSelection())
        dlg.Destroy()

    def onLoadDefaultPrompt(self, evt):
        load_default_prompt_helper(self.llmModel.GetValue(), self.llmPrompt, self.llmUserPrompt)
class CacheEntryDialog(wx.Dialog):
    def __init__(self, parent, title, source="", translation="", is_regexp=False):
        super().__init__(parent, title=title)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=mainSizer)
        
        self.sourceCtrl = sHelper.addLabeledControl(_("Source text:"), wx.TextCtrl, value=source)
        self.transCtrl = sHelper.addLabeledControl("Translation:", wx.TextCtrl, value=translation)
        
        self.regexpChk = sHelper.addItem(wx.CheckBox(self, label=_("Is Regular Expression")))
        self.regexpChk.SetValue(is_regexp)
        
        btnSizer = wx.StdDialogButtonSizer()
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.SetDefault()
        btnSizer.AddButton(btnOK)
        btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnSizer.AddButton(btnCancel)
        btnSizer.Realize()
        
        sHelper.addItem(btnSizer)
        
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        
    def onOK(self, evt):
        if self.regexpChk.GetValue():
            source = self.sourceCtrl.GetValue()
            try:
                prog = re.compile(source)
            except Exception as e:
                gui.messageBox(f_("Invalid regular expression:\n{e}"), _("Error"), style=wx.OK | wx.ICON_ERROR)
                return
                
            groups = prog.groups
            trans = self.transCtrl.GetValue()
            
            formatter = string.Formatter()
            for literal_text, field_name, format_spec, conversion in formatter.parse(trans):
                if field_name is not None:
                    if field_name.startswith('T') or field_name.startswith('P'):
                        try:
                            idx = int(field_name[1:])
                            if idx < 1 or idx > groups:
                                gui.messageBox(_("Token {{{field_name}}} refers to group {idx}, but the regex only has {groups} capture groups.").format(field_name=field_name, idx=idx, groups=groups), _("Error"), style=wx.OK | wx.ICON_ERROR)
                                return
                        except ValueError:
                            pass
        evt.Skip()
        
    def get_data(self):
        return {
            "source": self.sourceCtrl.GetValue(),
            "translation": self.transCtrl.GetValue(),
            "is_regexp": self.regexpChk.GetValue()
        }

class CacheEditorDialog(wx.Dialog):
    def __init__(self, parent, app_name, target_lang):
        super().__init__(parent, title=_("Cache Editor - {app_name} ({target_lang})").format(app_name=app_name, target_lang=target_lang).format(app_name=app_name, target_lang=target_lang), size=(600, 400))
        self.app_name = app_name
        self.target_lang = target_lang
        
        global_save = config.conf["YATA"].get("save_cache", True)
        app_save = global_save
        filepath = os.path.join(globalVars.appArgs.configPath, "YATA", "settings", f"{app_name}.ini")
        if os.path.exists(filepath):
            try:
                conf = configobj.ConfigObj(filepath)
                if "save_cache" in conf:
                    app_save = conf["save_cache"].lower() == 'true'
            except Exception:
                pass
        
        if not app_save:
            wx.CallAfter(gui.messageBox, _("Cache saving is disabled globally or for this application. Any changes made here are temporary and will be lost on restart unless cache saving is turned on."), _("Warning"), wx.OK | wx.ICON_WARNING)
            
        self.entries = cache.get_cache_entries(app_name, target_lang)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        self.listCtrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
        self.listCtrl.InsertColumn(0, _("Source text"), width=200)
        self.listCtrl.InsertColumn(1, _("Translation"), width=200)
        self.listCtrl.InsertColumn(2, _("Is Regex"), width=100)
        
        self.refresh_list()
        mainSizer.Add(self.listCtrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btnAdd = wx.Button(self, label=_("&Add"))
        btnAdd.Bind(wx.EVT_BUTTON, self.onAdd)
        btnSizer.Add(btnAdd, flag=wx.RIGHT, border=5)
        
        btnEdit = wx.Button(self, label=_("&Edit"))
        btnEdit.Bind(wx.EVT_BUTTON, self.onEdit)
        btnSizer.Add(btnEdit, flag=wx.RIGHT, border=5)
        
        btnDelete = wx.Button(self, label=_("&Delete"))
        btnDelete.Bind(wx.EVT_BUTTON, self.onDelete)
        btnSizer.Add(btnDelete, flag=wx.RIGHT, border=5)
        
        btnClear = wx.Button(self, label=_("&Clear Cache"))
        btnClear.Bind(wx.EVT_BUTTON, self.onClear)
        btnSizer.Add(btnClear)
        
        mainSizer.Add(btnSizer, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        
        stdBtnSizer = wx.StdDialogButtonSizer()
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.SetDefault()
        stdBtnSizer.AddButton(btnOK)
        btnCancel = wx.Button(self, wx.ID_CANCEL)
        stdBtnSizer.AddButton(btnCancel)
        stdBtnSizer.Realize()
        
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)
        
        mainSizer.Add(stdBtnSizer, flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        
        self.SetSizer(mainSizer)
        
    def refresh_list(self):
        self.listCtrl.DeleteAllItems()
        for i, entry in enumerate(self.entries):
            idx = self.listCtrl.InsertItem(i, entry.get("source", ""))
            self.listCtrl.SetItem(idx, 1, entry.get("translation", ""))
            self.listCtrl.SetItem(idx, 2, _("Yes") if entry.get("is_regexp") else _("No"))
            
    def onAdd(self, evt):
        dlg = CacheEntryDialog(self, _("Add Cache Entry"))
        if dlg.ShowModal() == wx.ID_OK:
            self.entries.append(dlg.get_data())
            self.refresh_list()
        dlg.Destroy()
        
    def onEdit(self, evt):
        idx = self.listCtrl.GetFirstSelected()
        if idx < 0: return
        entry = self.entries[idx]
        dlg = CacheEntryDialog(self, _("Edit Cache Entry"), source=entry.get("source", ""), translation=entry.get("translation", ""), is_regexp=entry.get("is_regexp", False))
        if dlg.ShowModal() == wx.ID_OK:
            self.entries[idx] = dlg.get_data()
            self.refresh_list()
        dlg.Destroy()
        
    def onDelete(self, evt):
        idx = self.listCtrl.GetFirstSelected()
        if idx < 0: return
        del self.entries[idx]
        self.refresh_list()
        
    def onClear(self, evt):
        if gui.messageBox(_("Are you sure you want to clear the entire cache for this app?"), _("Clear Cache"), style=wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            cache.clear_app_cache(self.app_name)
            self.entries = []
            self.refresh_list()
            
    def onOK(self, evt):
        app_cache = cache._cache.get(self.app_name, {})
        app_cache[self.target_lang] = self.entries
        cache._cache[self.app_name] = app_cache
        cache.save()
        self.Destroy()
        
    def onCancel(self, evt):
        self.Destroy()