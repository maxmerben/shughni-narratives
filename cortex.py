import json, os, re

DEFAULT_INDENT = 2


class Analysis():
    def __init__(self, json_dict):
        self.json = json_dict
        self.gloss = json_dict["gloss"]  if "gloss"  in json_dict else None
        self.parts = json_dict["parts"]  if "parts"  in json_dict else None
        if "gr.pos" in json_dict:
            if isinstance(json_dict["gr.pos"], str):
                self.grpos = [json_dict["gr.pos"]]
            else:
                self.grpos = json_dict["gr.pos"]
        else:
            self.grpos = None

        if "lex" in json_dict:
            self.lex = [json_dict["lex"]] if isinstance(json_dict["lex"], str) else json_dict["lex"]
        else:
            self.lex = None
        if "trans_en" in json_dict:
            self.trans_en = [json_dict["trans_en"]]\
                if "trans_en" in json_dict and isinstance(json_dict["trans_en"], str) else json_dict["trans_en"]
        else:
            self.trans_en = None
        
        self.gloss_index = json_dict["gloss_index"] if "gloss_index" in json_dict else None

    def __repr__(self):
        return json.dumps(self.json, indent=DEFAULT_INDENT, ensure_ascii=False)


class Token():
    def __init__(self, json_dict):
        self.json = json_dict
        self.wf = json_dict["wf"]
        self.off_start = json_dict["off_start"]
        self.off_end = json_dict["off_end"]
        self.wtype = json_dict["wtype"]                           if "wtype"              in json_dict else None
        self.next_word = json_dict["next_word"]                   if "next_word"          in json_dict else None
        self.sentence_index = json_dict["sentence_index"]         if "sentence_index"     in json_dict else None
        self.sentence_index_neg = json_dict["sentence_index_neg"] if "sentence_index_neg" in json_dict else None
        
        if "ana" in json_dict:
            self.ana = [Analysis(a) for a in json_dict["ana"]]
        else:
            self.ana = None
    
    
    def __repr__(self):
        return self.wf
        #return json.dumps(self.json, indent=DEFAULT_INDENT, ensure_ascii=False)

    def __getitem__(self, index):
        return self.ana[index]


class Sentence():
    def __init__(self, json_dict, translations=None):
        self.json = json_dict
        self.text = json_dict["text"]
        self.words = [Token(a) for a in json_dict["words"]]
        self.lang = json_dict["lang"]                      if "lang"           in json_dict else None
        self.meta = json_dict["meta"]                      if "meta"           in json_dict else None
        if "para_alignment" in json_dict:
            self.para_alignment = json_dict["para_alignment"][0]
        else:
            self.para_alignment = None
        self.src_alignment = json_dict["src_alignment"]    if "src_alignment"  in json_dict else None
        self.translations = translations

    def __repr__(self):
        return self.text
        #return json.dumps(self.json, indent=DEFAULT_INDENT, ensure_ascii=False)

    def __getitem__(self, index):
        return self.words[index]

    def __len__(self):
        return len(self.words)

    def search_gloss(self, glosses, whole=True, text_title=None, filename=None):
        if whole:
            re_q = "(?=[\-\=])|(?<=[\-\=])"
            no_q = ""
        else:
            re_q = "(?=[\.\-\=])|(?<=[\.\-\=])"
            no_q = "[^\-\=]*"
        results = []
        
        if isinstance(glosses, str):
            glosses = (glosses,)
        for gloss in glosses:
            for i_token in range(len(self.words)):
                ana = self.words[i_token].ana
                if not ana:
                    continue
                
                for i_ana in range(len(ana)):
                    if ana[i_ana].gloss is None:
                        continue
                    
                    query = re.search(
                        f"^{no_q}{gloss}{no_q}$|^{no_q}{gloss}{no_q}{re_q}{no_q}{gloss}{no_q}{re_q}{no_q}{gloss}{no_q}$",
                        ana[i_ana].gloss)
                    if not query:
                        continue
                    
                    try:
                        translation = self.translations[1]
                    except IndexError:
                        translation = None
                    results.append({
                        "match": query[0],
                        "gloss": ana[i_ana].gloss,
                        "wf": ana[i_ana].parts,
                        #"trans": ana[i_ana].trans_en,
                        "span_a": query.span()[0],
                        "span_b": query.span()[1],
                        "i_token": i_token,
                        "off_start": self.words[i_token].off_start,
                        "off_end": self.words[i_token].off_end,
                        "sentence": self.text,
                        "translation": translation,
                        "i_sentence": self.para_alignment["para_id"],
                        "text_title": text_title,
                        "filename": filename
                    })
        return results


class Text():
    def __init__(self, filepath):
        self.filepath = filepath
        self.json = json.load(open(filepath, "r", encoding="utf-8"))
        self.meta = self.json["meta"]
        self.filename = self.json["meta"]["filename"]
        
        self.title = self.json["meta"]["title"]       if "title"    in self.json["meta"] else None
        self.author = self.json["meta"]["author"]     if "author"   in self.json["meta"] else None
        self.source = self.json["meta"]["source"]     if "source"   in self.json["meta"] else None
        self.year = self.json["meta"]["year"]         if "year"     in self.json["meta"] else None
        self.genre = self.json["meta"]["genre"]       if "genre"    in self.json["meta"] else None
        self.adjusted = self.json["meta"]["adjusted"] if "adjusted" in self.json["meta"] else None
        self.parallel = self.json["meta"]["parallel"] if "parallel" in self.json["meta"] else None

        self.langs = set([a["lang"] for a in self.json["sentences"]])

        self.sentences = []
        for a in self.json["sentences"]:
            if a["lang"] == 0:
                translations = {}
                for b in self.json["sentences"]:
                    if b["lang"] != 0 and b["para_alignment"][0]["para_id"] == a["para_alignment"][0]["para_id"]:
                        translations[b["lang"]] = b["text"]
                self.sentences.append(Sentence(a, translations))

    def __repr__(self):
        return json.dumps(self.meta, indent=DEFAULT_INDENT, ensure_ascii=False)

    def __getitem__(self, index):
        return self.sentences[index]

    def __len__(self):
        return len(self.sentences)

    def search_gloss(self, glosses, whole=True):
        results = []
        for i_sent in range(len(self.sentences)):
            res = self.sentences[i_sent].search_gloss(
                glosses, whole, self.title, self.filename)
            results.extend(res)
        return results


class Corpus():
    def __init__(self, folderpath=""):
        self.folderpath = folderpath
        current_folder = os.path.dirname(os.path.abspath(__file__))
        abs_folderpath = os.path.join(current_folder, folderpath)
        files = []
        for f in os.listdir(abs_folderpath):
            if os.path.isfile(os.path.join(abs_folderpath, f)) and f.endswith(".json"):
                files.append(Text(os.path.join(abs_folderpath, f)))
        self.texts = files
        
    def __repr__(self):
        return str(self.texts)

    def __getitem__(self, index):
        return self.texts[index]

    def __len__(self):
        return len(self.texts)

    def search_gloss(self, glosses, whole=True):
        results = []
        for i_text in range(len(self.texts)):
            res = self.texts[i_text].search_gloss(glosses, whole)
            results.extend(res)
        return results
