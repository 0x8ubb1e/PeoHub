import os
import sys
import uuid
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox, simpledialog, Toplevel
from PIL import Image, ImageTk, ImageOps
from tinydb import TinyDB, Query, where

from pypinyin import lazy_pinyin

def sort_name(name):
	return lazy_pinyin(name.lower())

# =========== 常量 ===========
# ROOT_DIR = Path(__file__).parent
# ROOT_DIR = Path(__file__).resolve().parent  # EXE 同级目录
# # 无论 exe 还是脚本，始终取“可执行文件”所在目录
# ROOT_DIR = Path(getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__))))
# ROOT_DIR = Path(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
ROOT_DIR = Path.cwd()  # 始终指向“运行目录”

DB_PATH = ROOT_DIR / "people.json"
TRASH_DB = ROOT_DIR / "trash.json"
IMG_DIR = ROOT_DIR / "images"
IMG_DIR.mkdir(exist_ok=True)
DEFAULT_AVATAR = IMG_DIR / "default.png"
if not DEFAULT_AVATAR.exists():
	Image.new("RGB", (150, 150), "#555555").save(DEFAULT_AVATAR)

db = TinyDB(DB_PATH, encoding="utf-8", ensure_ascii=False)
Person = Query()

trash_db = TinyDB(TRASH_DB, encoding="utf-8", ensure_ascii=False)
Trash = Query()

def center(win):
	win.update_idletasks()
	# print(f"windows: {win.winfo_screenwidth()}x{win.winfo_screenheight()}")
	# print(f"box: {win.winfo_width}x{win.winfo_height()}")
	x = (win.winfo_screenwidth() - win.winfo_width()) // 2
	y = (win.winfo_screenheight() - win.winfo_height()) // 2
	# print(f"position: {x}x{y}")
	win.geometry(f"+{x}+{y}")

def load_image(path, size=(120, 160)):
	"""保持长宽比完整填充 size"""
	try:
		img = Image.open(path).convert("RGB")
		return ImageTk.PhotoImage(ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.5)))
	except:
		return ImageTk.PhotoImage(Image.new("RGB", size, "#555555"))

def all_schools():
	return sorted({edu["school"] for p in db.all() for edu in p.get("educations", [])})

def set_dark(root):
	style = ttk.Style(root)
	style.theme_use("clam")
	style.configure(".", background="#2e2e2e", foreground="#ccc", fieldbackground="#3c3c3c")
	style.map(".", background=[("active", "#444")])

def ask_centered(title, prompt):
	root = Toplevel()
	root.withdraw()  # 隐藏主窗口
	dlg = simpledialog.askstring(title, prompt, parent=root)
	if dlg:
		root.update_idletasks()
		x = (root.winfo_screenwidth() - 300) // 2
		y = (root.winfo_screenheight() - 100) // 2
		root.geometry(f"+{x}+{y}")
	root.destroy()
	return dlg

# =========== 主窗口 ===========
class MainWindow(Tk):
	def __init__(self):
		super().__init__()
		self.title("人物管理器")
		set_dark(self)
		self.selected_id = None  # 当前选中人物 uuid

		# 顶部工具栏
		top_bar = Frame(self, bg="#2e2e2e")
		top_bar.pack(fill=X, padx=10)
		Button(top_bar, text="新建人物", command=self.new_person, bg="#444", fg="#ccc").pack(side=LEFT, padx=5, pady=2)
		Button(top_bar, text="刷新", command=self.refresh_all, bg="#444", fg="#ccc").pack(side=LEFT, padx=5, pady=2)

		# PanedWindow
		paned = PanedWindow(self, orient=HORIZONTAL, sashrelief=RAISED, sashwidth=10, bg="#2e2e2e")
		paned.pack(fill=BOTH, expand=True, padx=10, pady=1)

		# 左侧人物列表
		left = Frame(paned, bg="#2e2e2e", width=175)
		left.pack_propagate(False)  # ← 关键：禁止子控件撑大
		paned.add(left)
		# self.people_list = Listbox(left, font=("微软雅黑", 12), bg="#2e2e2e", fg="#ccc", selectbackground="#555")
		# self.people_list.pack(fill=BOTH, expand=True, padx=5, pady=5)
		self.people_tree = ttk.Treeview(left, show="tree", height=15, selectmode="browse")
		self.people_tree.pack(fill=BOTH, expand=True, padx=2, pady=2)
		
		# 样式：去掉下划线
		style = ttk.Style()
		style.configure("Treeview", font=("微软雅黑", 12), background="#2e2e2e", foreground="#ccc", fieldbackground="#2e2e2e", highlightthickness=0, relief="flat", indent=0, padding=0)
		style.map("Treeview", background=[("selected", "#555")], foreground=[("selected", "#ccc")])
		# self.people_list.bind("<<ListboxSelect>>", self.on_select)
		self.people_tree.bind("<<TreeviewSelect>>", self.on_select)
		self.people_tree.bind("<Button-3>", self.on_people_right)

		# 回收区
		trash_frame = LabelFrame(left, text="回收区", bg="#2e2e2e", fg="#ccc")
		trash_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

		# 文件夹/人物树
		# self.trash_tree = Listbox(trash_frame, font=("微软雅黑", 12),bg="#2e2e2e", fg="#ccc", selectbackground="#555555")
		# self.trash_tree.pack(fill=BOTH, expand=True, padx=2, pady=2)
		# self.trash_tree.bind("<Button-3>", self.on_trash_right)
		self.trash_tree = ttk.Treeview(trash_frame, show="tree", height=8, selectmode="browse")
		self.trash_tree.pack(fill=BOTH, expand=True, padx=2, pady=2)
		self.trash_tree.bind("<<TreeviewSelect>>", self.on_select)
		self.trash_tree.bind("<Button-3>", self.on_trash_right)

		# 计数标签
		self.count_label = Label(left, text="", bg="#2e2e2e", fg="#ccc")
		self.count_label.pack(side=LEFT, padx=10)

		# 右侧详情
		right = Frame(paned, bg="#2e2e2e")
		paned.add(right)
		self.detail = PersonDetail(right, self)
		self.detail.pack(fill=BOTH, expand=True, padx=10, pady=10)

		self.refresh_all()
		center(self)

		# # 右键置顶
		# self.people_list.bind("<Button-3>", self.pop_menu)
		# self.popup = Menu(self, tearoff=0)
		# self.popup.add_command(label="置顶", command=self.set_top)
		# self.popup.add_command(label="取消置顶", command=self.cancel_top)
		# self.popup.add_command(label="放入回收站", command=self.move_to_trash)

	def on_select(self, evt):
		w = evt.widget

		# 忽略刷新时的空选
		if not w.selection():
			return
		item = w.selection()[0]
		uuid = w.item(item, "tags")[0]
		self.selected_id = uuid
		self.detail.load_person(uuid)

	# =========== 任务列表 ===========
	def on_people_right(self, event):  # 人物列表右键
		# idx = self.people_list.nearest(event.y)
		item = self.people_tree.identify_row(event.y)

		uuid = self.people_tree.item(item, "tags")[0]
		person = db.get(where("id") == uuid)

		menu = Menu(self, tearoff=0)
		menu.add_command(label="新建人物", command=self.new_person)
		menu.add_command(label="置顶", command=lambda: self.set_top(person["id"]))
		menu.add_command(label="取消置顶", command=lambda: self.cancel_top(person["id"]))
		menu.add_command(label="放入回收站", command=lambda: self.move_to_trash(person["id"]))
		menu.post(event.x_root, event.y_root)

	def new_person(self):
		pid = str(uuid.uuid4())
		db.insert({
			"id": pid, "name": "新人物", "phone": "", "email": "", "birth": "", "id_card": "", "address": "", "global_note": "", "avatar": str(DEFAULT_AVATAR), "educations": [], "socials": []
		})
		self.selected_id = pid
		self.refresh_all()
		# self.people_list.selection_clear(0, END)
		# self.people_list.selection_set(END)
		# self.people_list.event_generate("<<ListboxSelect>>")
	
	def set_top(self, person_id: str):
		db.update({"top": True}, where("id") == person_id)
		self.selected_id = person_id
		self.refresh_all()

	def cancel_top(self, person_id):
		db.update({"top": False}, where("id") == person_id)
		self.selected_id = person_id
		self.refresh_all()
	
	def move_to_trash(self, person_id):
		person = db.get(where("id") == person_id)
		if not person:
			return

		# 询问放入哪个文件夹或新建
		folder_name = ask_centered("放入回收站", "文件夹名称（空＝根目录）：")
		if not folder_name:
			trash_db.insert({"type": "person", **person})
		else:  # 创建/追加文件夹
			folder = trash_db.search((Trash.type == "folder") & (Trash.name == folder_name))
			if not folder:
				trash_db.insert({"type": "folder", "name": folder_name, "items": [person]})
			else:
				folder[0]["items"].append(person)
				trash_db.update({"items": folder[0]["items"]}, (Trash.type == "folder") & (Trash.name == folder_name))
		
		db.remove(where("id") == person_id)
		self.selected_id = None  # 或保留
		self.refresh_all()

	# =========== 回收站 ===========
	def on_trash_right(self, event):
		item = self.trash_tree.identify_row(event.y)
		menu = Menu(self, tearoff=0)
		
		menu.add_command(label="新建文件夹", command=self.new_trash_folder)

		# 获取文本
		text = self.trash_tree.item(item, "text")
		if "👤" in text:
			name = text.replace("👤", "").strip()
			person = next((p for r in trash_db.all()
				for p in ([r] if r["type"] == "person" else r.get("items", []))
				if p.get("name") == name), None)
			if person:
				menu.add_command(label="还原", command=lambda: self.restore_person(person["id"]))
		elif "📁" in text:
			folder_name = text.replace("📁", "").strip()
			menu.add_command(label="删除文件夹", command=lambda: self.delete_folder(folder_name))
		menu.post(event.x_root, event.y_root)

	def new_trash_folder(self):
		name = ask_centered("新建文件夹", "文件夹名称：")

		if name:
			trash_db.insert({"type": "folder", "name": name, "items": []})
			self.refresh_trash()

	def restore_person(self, person_id):
		# person = db.get(where("id") == person_id)
		person = next((p for r in trash_db.all()
			for p in ([r] if r["type"] == "person" else r.get("items", []))
			if p["id"] == person_id), None)
		if person:
			db.insert(person)
			trash_db.remove(where("id") == person_id)  # 只删一个

			self.selected_id = person["id"]
			self.refresh_all()
			messagebox.showinfo("提示", f"{person['name']} 已还原！")

	def delete_folder(self, folder_name):
		trash_db.remove((Trash.type == "folder") & (Trash.name == folder_name))
		self.refresh_trash()

	# =========== 刷新数据 ===========
	def refresh_all(self):
		if not DB_PATH.exists():
			TinyDB(DB_PATH, ensure_ascii=False).insert({})
			messagebox.showinfo("提示", "数据库文件已创建！")
		if not TRASH_DB.exists():
			TinyDB(TRASH_DB, ensure_ascii=False).insert({})
			messagebox.showinfo("提示", "回收站文件已创建！")
		self.detail.clear()  # 清空详情，避免脏数据
		self.refresh_people()
		self.refresh_trash()

	def refresh_people(self):  # 刷新列表：置顶在前，其余按字母排序
		# self.people_list.delete(0, END)
		self.people_tree.delete(*self.people_tree.get_children())

		data = db.all()
		# self.uuid2idx = {p["id"]: i for i, p in enumerate(data)}  # uuid -> Listbox 行号
		news = [p for p in data if p.get("name") == "新人物"]
		tops = [p for p in data if p.get("top") and p.get("name") != "新人物"]
		others = [p for p in data if not p.get("top") and p.get("name") != "新人物"]
		tops.sort(key=lambda x: sort_name(x["name"]))
		others.sort(key=lambda x: sort_name(x["name"]))
		self.all_people = news + tops + others
		# print([f'{p.get("name")}({p.get("id")})' for p in self.all_people])

		for idx, p in enumerate(self.all_people):
			# self.people_list.insert(END, f'👤 {p["name"]}    ⭐'  if p.get("top") else f'👤 {p["name"]}')
			self.people_tree.insert("", "end", text=f'👤 {p["name"]}    ⭐'  if p.get("top") else f'👤 {p["name"]}', tags=(p["id"],))
			self.uuid2idx = {p["id"]: idx}
		
		# 定位 select_id
		if not self.selected_id:
			if not len(self.people_tree.get_children()):
				self.detail.load_person(None)
				return
			else:
				idx = self.idx_from_uuid(self.all_people[0]["id"])
				print(f'当前未选中用户, 正在展示用户idx: {idx}\n{self.all_people[0]}')
		else:
			print(f'正在展示用户uuid: {self.selected_id}')
			idx = next((i for i, p in enumerate(self.all_people) if p["id"] == self.selected_id), 0)

		# # self.people_list.selection_set(idx)
		# self.scroll_to_uuid(self.all_people[0]["id"])
		# print(f"当前未选中用户，默认展示列表第一个用户idx: {idx} uuid: {self.all_people[0]['id']}")
		# self.selected_id = data[idx]["id"]
		# self.detail.load_person(self.selected_id)
		# print(f"当前选中idx: {idx} 用户uuid： {self.selected_id}")

		item = self.people_tree.get_children()[idx]
		# print(item)
		self.people_tree.selection_set(item)
		self.people_tree.see(item)
		self.selected_id = self.all_people[idx]["id"]
		self.detail.load_person(self.selected_id)  # 只刷新详情，不触发事件
		
		# 更新计数条
		total = len(db.all())
		trash_total = len(trash_db.search(Trash.type == "person"))
		self.count_label.config(text=f"人物:{total} 回收站:{trash_total}")

	def refresh_trash(self):
		# self.trash_tree.delete(0, END)
		# folders = trash_db.search(Trash.type == "folder")
		# persons = trash_db.search(Trash.type == "person")
		# for f in folders:
		# 	self.trash_tree.insert(END, f'📁 {f["name"]}')
		# 	for p in f["items"]:
		# 		self.trash_tree.insert(END, f' 👤 {p["name"]}')
		
		# for p in persons:
		# 	self.trash_tree.insert(END, f'👤 {p["name"]}')

		self.trash_tree.delete(*self.trash_tree.get_children())
		# 根目录人物
		for p in trash_db.search(Trash.type == "person"):
			self.trash_tree.insert("", "end", text=f"👤 {p['name']}", values=(str(p),))
		# 文件夹
		for f in trash_db.search(Trash.type == "folder"):
			fid = self.trash_tree.insert("", "end", text=f"📁 {f['name']}")
			for p in f["items"]:
				self.trash_tree.insert(fid, "end", text=f" 👤 {p['name']}", values=(str(p),))

	def idx_from_uuid(self, uuid: str) -> int:
		return self.uuid2idx.get(uuid, 0)
	
	def scroll_to_uuid(self, uuid: str):
		for item in self.people_tree.get_children():
			if self.people_tree.item(item, "tags")[0] == uuid:
				self.people_tree.selection_set(item)
				self.people_tree.see(item)
				return
	
class PersonDetail(Frame):
	def __init__(self, parent, master):
		super().__init__(parent)
		self.master: MainWindow = master
		self.current_id = None
		self.count = 3
		self.configure(bg="#2e2e2e")
		self.build()

	def build(self):
		basic = LabelFrame(self, text="基本信息", bg="#2e2e2e", fg="#ccc")
		basic.pack(fill=X, padx=10, pady=5)

		# 左侧头像 3:4
		avatar_frame = Frame(basic, width=120, height=160, bg="#2e2e2e")
		avatar_frame.pack_propagate(False)
		avatar_frame.pack(side=LEFT, fill=Y, padx=10, pady=10)
		self.avatar_btn = Button(avatar_frame, command=self.change_avatar, bd=0, relief=FLAT)
		self.avatar_btn.pack(fill=BOTH, expand=True)

		# 右侧 3×3 网格
		right_info = Frame(basic, bg="#2e2e2e")
		right_info.pack(side=LEFT, fill=BOTH, expand=True, padx=10)

		fields = [("姓名", "name"), ("电话", "phone"), ("邮件", "email"), ("生日", "birth"), ("身份证", "id_card"), ("地址", "address")]
		self.basic_vars = {}
		for idx, (label, key) in enumerate(fields):
			Label(right_info, text=label, bg="#2e2e2e", fg="#ccc").grid(row=idx // self.count, column=idx % self.count * 2, sticky=E, padx=5, pady=2)
			var = StringVar()
			Entry(right_info, textvariable=var, width=22).grid(row=idx // self.count, column=idx % self.count * 2 + 1, padx=5, pady=2)
			self.basic_vars[key] = var

		# 备注占整行
		row = idx // self.count
		Label(right_info, text="备注", bg="#2e2e2e", fg="#ccc").grid(row=row+1, column=1, sticky=W, padx=4, pady=2)
		self.note_text = Text(right_info, height=3, wrap=WORD, bg="#3c3c3c", fg="#ccc")
		self.note_text.grid(row=row+2, column=1, columnspan=self.count * 2, sticky=EW, padx=2, pady=2)

		btn_frame = Frame(right_info, bg="#2e2e2e")
		btn_frame.grid(row=row+3, column=1, columnspan=4, pady=6, sticky=E)
		Button(btn_frame, text="保存基本信息", bg="#444", fg="#ccc", command=self.save_basic).pack(side=LEFT, padx=5)
		Button(btn_frame, text="删除人物", bg="#cc3333", fg="#ccc", command=self.delete_person).pack(side=LEFT, padx=5)

		# 教育经历
		edu = LabelFrame(self, text="教育经历", bg="#2e2e2e", fg="#ccc")
		edu.pack(fill=X, padx=10, pady=2)
		self.edu_tree = ttk.Treeview(edu, columns=("stage", "school", "year", "major", "class_name", "student_id", "thesis", "note"), show="headings", height=3)
		self.edu_tree.pack(fill=BOTH, expand=True)
		heads = {"stage": ("阶段", CENTER), "school": ("学校", W), "year": ("年份", CENTER), "major": ("专业", CENTER), "class_name": ("班级", CENTER), "student_id": ("学号", CENTER), "thesis": ("毕业论文", W), "note": ("备注", W)}
		for col, (txt, anchor) in heads.items():
			self.edu_tree.heading(col, text=txt)
			self.edu_tree.column(col, width=70 if col != "note" else 120, anchor=anchor)
		
		btn_bar = Frame(edu, bg="#2e2e2e")
		btn_bar.pack(fill=X, pady=2)
		Button(btn_bar, text="添加", command=lambda: EduDialog(self)).pack(side=LEFT, padx=2)
		Button(btn_bar, text="编辑", command=self.edit_edu).pack(side=LEFT, padx=2)
		Button(btn_bar, text="删除", command=self.delete_edu).pack(side=LEFT, padx=2)

		# 社交媒体
		social = LabelFrame(self, text="社交媒体", bg="#2e2e2e", fg="#ccc")
		social.pack(fill=X, padx=10, pady=2)
		self.social_tree = ttk.Treeview(social, columns=("platform", "account", "nickname", "url", "signature", "img_dir"), show="headings", height=4)
		self.social_tree.pack(fill=BOTH, expand=True)
		heads = {"platform": ("平台", CENTER), "account": ("账号", CENTER), "nickname": ("昵称", W), "url": ("URL", W), "signature": ("签名", W), "img_dir": ("图片目录", W)}
		for col, (txt, anchor) in heads.items():
			self.social_tree.heading(col, text=txt)
			self.social_tree.column(col, width=80 if col != "img_dir" else 120, anchor=anchor)
		
		btn_bar2 = Frame(social, bg="#2e2e2e")
		btn_bar2.pack(fill=X, pady=2)
		Button(btn_bar2, text="添加", command=lambda: SocialDialog(self)).pack(side=LEFT, padx=2)
		Button(btn_bar2, text="编辑", command=self.edit_social).pack(side=LEFT, padx=2)
		Button(btn_bar2, text="删除", command=self.delete_social).pack(side=LEFT, padx=2)

	# =========== 通用 ===========
	def load_person(self, person_id: str):
		person = db.get(where("id") == person_id)
		if not person:
			self.clear(); return
		self.current_id = person_id
	
		for k, var in self.basic_vars.items():
			var.set(person.get(k, ""))
		self.note_text.delete(1.0, END)
		self.note_text.insert(1.0, person.get("global_note", ""))
		self.show_avatar(person["avatar"])
		self.refresh_edu(person.get("educations", []))
		self.refresh_social(person.get("socials", []))
		print(f"加载用户 {person.get('name')}({person_id}) 成功！")

	def clear(self):
		self.current_id = None
		for var in self.basic_vars.values(): var.set("")
		self.note_text.delete(1.0, END)
		self.show_avatar(str(DEFAULT_AVATAR))
		self.refresh_edu([])
		self.refresh_social([])

	def show_avatar(self, path):
		self.avatar_img = load_image(path, (150, 150))
		self.avatar_btn.config(image=self.avatar_img, width=150, height=150)

	def change_avatar(self):
		f = filedialog.askopenfilename(title="选择头像", filetypes=[("图片", "*.jpg *.png *.jpeg *.bmp")])
		if f:
			CropWindow(self, f, self.current_id, self)

	def save_basic(self):
		if not self.current_id: return
		data = {k: var.get().strip() for k, var in self.basic_vars.items()}
		data["global_note"] = self.note_text.get(1.0, END).strip()
		db.update(data, where("id") == self.current_id)
		self.master.refresh_all()

	def delete_person(self):
		if not self.current_id:
			return
		person = db.get(where("id") == self.current_id)
		if person and messagebox.askyesno("确认", f"删除 {person['name']}？"):
			db.remove(where("id") == self.current_id)
			self.master.refresh_all()

	def refresh_edu(self, educations):
		for item in self.edu_tree.get_children(): self.edu_tree.delete(item)
		for edu in educations:
			self.edu_tree.insert("", END, values=(
				edu["stage"], edu["school"], f"{edu.get('start', '')}-{edu.get('end', '')}", edu.get("major", ""), edu.get("class_name", ""), edu.get("student_id", ""), edu.get("thesis", ""), edu.get("note", "")
			))

	def edit_edu(self):
		sel = self.edu_tree.selection()
		if not sel: return
		idx = self.edu_tree.index(sel[0])
		item = self.edu_tree.item(sel[0])
		values = item["values"]
		EduDialog(self, {
			"stage": values[0], "school": values[1], 
			"start": int(values[2].split("-")[0]) if values[2] != "-" else None,
			"end": int(values[2].split("-")[1]) if values[2] != "-" else None,
			"major": values[3], "class_name": values[4], "student_id": values[5],
			"thesis": values[6], "note": values[7], "index": idx
		})

	def delete_edu(self):
		sel = self.edu_tree.selection()
		if not sel: return
		idx = self.edu_tree.index(sel[0])
		person = db.get(where("id") == self.current_id)
		educations = person["educations"]
		del educations[idx]
		db.update({"educations": educations}, where("id") == self.current_id)
		self.refresh_edu(educations)

	def refresh_social(self, socials):
		for item in self.social_tree.get_children(): self.social_tree.delete(item)
		for s in socials:
			self.social_tree.insert("", END, values=(
				s["platform"], s["account"], s["nickname"], s.get("url", ""),
				s.get("signature", ""), s.get("img_dir", "")
			))

	def edit_social(self):
		sel = self.social_tree.selection()
		if not sel: return
		idx = self.social_tree.index(sel[0])
		item = self.social_tree.item(sel[0])
		values = item["values"]
		SocialDialog(self, {
			"platform": values[0], "account": values[1], "nickname": values[2],
			"url": values[3], "signature": values[4], "img_dir": values[5], 
			"index": idx
		})

	def delete_social(self):
		sel = self.social_tree.selection()
		if not sel: return
		idx = self.social_tree.index(sel[0])
		person = db.get(where("id") == self.current_id)
		socials = person.get("socials", [])
		del socials[idx]
		db.update({"socials": socials}, where("id") == self.current_id)
		self.refresh_social(socials)

# =========== 头像裁剪窗口 ===========
class CropWindow(Toplevel):
	MODE_FREE = "自由"
	MODE_FIXED = "固定"

	def __init__(self, parent, img_path, person_id, detail_ref):
		super().__init__(parent)
		self.title("裁剪头像")
		self.configure(bg="#2e2e2e")
		self.grab_set()

		# 基础
		self.person_id = person_id
		self.detail_ref = detail_ref
		self.original = Image.open(img_path).convert("RGB")
		self.scale = 1.0
		self.mode = self.MODE_FIXED
		self.rect = {"x": 0, "y": 0, "w": 120, "h": 160}
		self.drag_img = self.drag_rect = self.resize_rect = False
		self.start_x = self.start_y = 0

		# 自适应窗口大小
		base_w, base_h = min(800, self.original.width), min(600, self.original.height)
		self.scale = min(base_w / self.original.width, base_h / self.original.height)
		self.display_w = int(self.original.width * self.scale)
		self.display_h = int(self.original.height * self.scale)
		self.geometry(f"{self.display_w + 20}x{self.display_h + 70}")
		self.update_idletasks()
		x = (self.winfo_screenwidth() - self.winfo_width()) // 2
		y = (self.winfo_screenheight() - self.winfo_height()) // 2
		self.geometry(f"+{x}+{y}")

		# 顶部工具栏
		bar = Frame(self, bg="#2e2e2e")
		bar.pack(side=TOP, fill=X, padx=5, pady=2)
		self.btn_fixed = Button(bar, text=self.MODE_FIXED, command=lambda: self.set_mode(self.MODE_FIXED), relief=GROOVE, bg="#0078d4", fg="#ccc")
		self.btn_fixed.pack(side=LEFT, padx=3)
		self.btn_free = Button(bar, text=self.MODE_FREE, command=lambda: self.set_mode(self.MODE_FREE), relief=GROOVE, bg="#555555", fg="#ccc")
		self.btn_free.pack(side=LEFT, padx=3)
		Button(bar, text="关于", command=self.show_about, bg="#444", fg="#ccc").pack(side=RIGHT, padx=3)

		# 画布（无留白）
		self.canvas = Canvas(self, width=self.display_w, height=self.display_h, bg="#2e2e2e", highlightthickness=0)
		self.canvas.pack()

		self.canvas.bind("<Button-1>", self.on_left_down)
		self.canvas.bind("<B1-Motion>", self.on_left_move)
		self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
		self.canvas.bind("<MouseWheel>", self.on_scroll)
		self.canvas.bind("<Motion>", self.on_motion)
		if self.mode == self.MODE_FREE:
			self.canvas.bind("<Button-3>", self.on_right)

		# 底部
		bottom = Frame(self, bg="#2e2e2e")
		bottom.pack(side=BOTTOM, fill=X, padx=5, pady=2)
		self.info_label = Label(bottom, text="", bg="#2e2e2e", fg="#ccc")
		self.info_label.pack(side=LEFT)
		Button(bottom, text="确认裁剪", bg="#444", fg="#ccc", command=self.crop).pack(side=RIGHT)

		self.redraw()

	# =========== 工具 ===========
	def show_about(self):
		messagebox.showinfo(
			"操作提示",
			"• 左键：移动图片 / 移动选框 / 8向缩放（自由）\n"
			"• Ctrl/Alt+左键：自由模式画框\n"
			"• 右键：自由模式清除框\n"
			"• 中键：缩放图片"
		)

	def set_mode(self, mode):
		self.mode = mode
		self.btn_free.config(bg="#0078d4" if mode == self.MODE_FREE else "#555555")
		self.btn_fixed.config(bg="#0078d4" if mode == self.MODE_FIXED else "#555555")
		if mode == self.MODE_FIXED:
			self.rect = {"x": 0, "y": 0, "w": 120, "h": 160}
		if mode == self.MODE_FREE:
			self.canvas.bind("<Button-3>", self.on_right)
		else:
			self.canvas.unbind("<Button-3>")
		self.redraw()

	def redraw(self):
		self.canvas.delete("all")
		w, h = self.original.size
		dw, dh = int(w * self.scale), int(h * self.scale)
		self.tk_img = ImageTk.PhotoImage(self.original.resize((dw, dh), Image.LANCZOS))
		self.canvas.create_image(0, 0, anchor=NW, image=self.tk_img)
		if self.rect:
			x, y, w, h = self.rect["x"], self.rect["y"], self.rect["w"], self.rect["h"]
			self.canvas.create_rectangle(x, y, x + w, y + h, outline="red", width=2)
		# self.info_label.config(text=f"{self.rect['w']}×{self.rect['h']}  缩放{self.scale:.2f}x" if self.rect else f"缩放{self.scale:.2f}x")
		self.info_label.config(text=f"{self.rect['w']}×{self.rect['h']} {self.scale:.2f}x")

	def on_left_down(self, event):
		x, y = event.x, event.y
		self.start_x, self.start_y = x, y
		if self.mode == self.MODE_FREE and (event.state & 0x0004 or event.state & 0x0008):
			self.rect = {"x": x, "y": y, "w": 0, "h": 0}
			self.drawing = True
		else:
			if self.rect and self.hit_resize(x, y):
				self.resize_rect = True
				self.resize_dir = self.get_resize_dir(x, y)
			elif self.rect and self.hit_move(x, y):
				self.drag_rect = True
			else:
				self.drag_img = True

	def on_left_move(self, event):
		x, y = event.x, event.y
		dx, dy = x - self.start_x, y - self.start_y
		if self.drawing:  # 画框
			self.rect["w"], self.rect["h"] = abs(x - self.rect["x"]), abs(y - self.rect["y"])
			self.redraw()
		elif self.drag_img:  # 移动图片
			self.rect["x"] += dx
			self.rect["y"] += dy
			self.start_x, self.start_y = x, y
			self.redraw()
		elif self.drag_rect:  # 移动选框
			self.rect["x"] += dx
			self.rect["y"] += dy
			self.start_x, self.start_y = x, y
			self.redraw()
		elif self.resize_rect and self.mode == self.MODE_FREE:  # 8方向缩放
			r = self.rect
			r["w"] = max(10, r["w"] + dx)
			r["h"] = max(10, r["h"] + dy)
			self.start_x, self.start_y = x, y
			self.redraw()

	def on_left_up(self, event):
		self.drawing = self.drag_img = self.drag_rect = self.resize_rect = False

	def on_scroll(self, event):
		factor = 1.1 if event.delta > 0 else 0.9
		# self.scale = max(0.2, min(5.0, self.scale * factor))
		# self.redraw()

		w, h = self.original.size
		box_w, box_h = self.rect["w"], self.rect["h"]
		# 计算“刚好填满”时的最大比例
		min_scale = min(box_w / w, box_h / h)
		# 只允许放大，或缩小到 min_scale
		self.scale = max(min_scale, min(5.0, self.scale * factor))
		self.redraw()

	def on_right(self, event):
		if self.mode == self.MODE_FREE:
			self.rect = None
			self.redraw()

	def on_motion(self, event):
		x, y = event.x, event.y
		if not self.rect:
			self.config(cursor="arrow"); return
		dirs = []
		r = self.rect
		if abs(x - r["x"]) < 10: dirs.append("w")
		if abs(x - (r["x"] + r["w"])) < 10: dirs.append("e")
		if abs(y - r["y"]) < 10: dirs.append("n")
		if abs(y - (r["y"] + r["h"])) < 10: dirs.append("s")
		if dirs:
			self.config(cursor="".join(dirs))
		elif r["x"] <= x <= r["x"] + r["w"] and r["y"] <= y <= r["y"] + r["h"]:
			self.config(cursor="fleur")
		else:
			self.config(cursor="arrow")

	def hit_resize(self, x, y):
		r = self.rect
		return any([abs(x - r["x"]) < 10, abs(x - (r["x"] + r["w"])) < 10, abs(y - r["y"]) < 10, abs(y - (r["y"] + r["h"])) < 10])

	def hit_move(self, x, y):
		r = self.rect
		return r["x"] <= x <= r["x"] + r["w"] and r["y"] <= y <= r["y"] + r["h"]

	def crop(self):
		if not self.rect:
			messagebox.showwarning("提示", "请先框选区域"); return
		r = self.rect
		x1, y1, x2, y2 = [max(0, int(v / self.scale)) for v in (r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])]

		# 高清：先原图裁剪，再缩放
		# cropped = self.original.crop((x1, y1, x2, y2)).resize((120, 160), Image.LANCZOS)
		# target = IMG_DIR / (str(uuid.uuid4()) + ".jpg")
		# cropped.save(target)
		cropped = self.original.crop((x1, y1, x2, y2))
		target = IMG_DIR / (str(uuid.uuid4()) + ".jpg")
		cropped.save(target, quality=95)  # 不二次压缩

		db.update({"avatar": str(target)}, where("id") == self.person_id)
		self.detail_ref.show_avatar(str(target))
		self.destroy()

# =========== 教育经历弹窗 ===========
class EduDialog(Toplevel):
	def __init__(self, parent, edu=None):
		super().__init__(parent)
		self.parent = parent
		self.edu = edu or {}
		self.title("教育经历")
		self.geometry("500x420")
		self.configure(bg="#2e2e2e")
		center(self)
		self.grab_set()
		self.build()
		self.load()
		self.on_stage_change()

	def build(self):
		label_pairs = [("阶段 *", "stage"), ("学校 *", "school"), ("开始年份", "start"), ("结束年份", "end"), ("专业", "major"), ("班级", "class_name"), ("学号", "student_id"), ("毕业论文", "thesis"), ("备注", "note")]
		self.vars = {}
		for i, (label_txt, key) in enumerate(label_pairs):
			Label(self, text=label_txt, bg="#2e2e2e", fg="#ccc").grid(row=i, column=0, sticky=E, padx=10, pady=4)
			if key == "school":
				self.school_combo = ttk.Combobox(self, width=23)
				self.school_combo["values"] = all_schools()
				self.school_combo.grid(row=i, column=1, sticky=W, padx=10, pady=4)
				self.vars[key] = self.school_combo
			elif key == "stage":
				self.stage_combo = ttk.Combobox(self, values=["小学", "初中", "高中", "本科", "硕士", "博士"], width=23)
				self.stage_combo.grid(row=i, column=1, sticky=W, padx=10, pady=4)
				self.vars[key] = self.stage_combo
				self.stage_combo.bind("<<ComboboxSelected>>", self.on_stage_change)
			elif key == "note":
				txt = Text(self, width=27, height=3, wrap=WORD, bg="#3c3c3c", fg="#ccc")
				txt.grid(row=i, column=1, sticky=W, padx=10, pady=4)
				self.vars[key] = txt
			else:
				var = StringVar()
				Entry(self, textvariable=var, width=23).grid(row=i, column=1, sticky=W, padx=10, pady=4)
				self.vars[key] = var
		Button(self, text="确认", bg="#444", fg="#ccc", command=self.ok).grid(row=len(label_pairs), column=0, columnspan=2, pady=10)

	def load(self):
		if self.edu:
			self.stage_combo.set(self.edu["stage"])
			self.school_combo.set(self.edu["school"])
			self.vars["start"].set(str(self.edu.get("start", "")))
			self.vars["end"].set(str(self.edu.get("end", "")))
			self.vars["major"].set(self.edu.get("major", ""))
			self.vars["class"].set(self.edu.get("class_name", ""))
			self.vars["student_id"].set(self.edu.get("student_id", ""))
			self.vars["毕业论文"].set(self.edu.get("thesis", ""))
			self.vars["note"].insert(1.0, self.edu.get("note", ""))
		else:
			self.stage_combo.set("本科")
		self.on_stage_change()

	def on_stage_change(self, event=None):
		stage = self.vars["stage"].get()
		for key in ("major", "thesis"):
			ent = self.vars[key]
			if isinstance(ent, Entry):
				ent.config(state=NORMAL if stage in {"本科", "硕士", "博士"} else DISABLED)

	def ok(self):
		stage = self.vars["stage"].get().strip()
		school = self.vars["school"].get().strip()
		if not (stage and school):
			messagebox.showwarning("提示", "阶段和学校为必填项"); return
		
		new_edu = {
			"stage": stage, "school": school,
			"start": int(self.vars["start"].get()) if self.vars["start"].get().isdigit() else None,
			"end": int(self.vars["end"].get()) if self.vars["end"].get().isdigit() else None,
			"major": self.vars["major"].get().strip(),
			"class_name": self.vars["class_name"].get().strip(),
			"student_id": self.vars["student_id"].get().strip(),
			"thesis": self.vars["thesis"].get().strip(),
			"note": self.vars["note"].get(1.0, END).strip()
		}
		person = db.get(where("id") == self.parent.current_id)
		educations = person["educations"]
		if self.edu:
			idx = self.edu["index"]
			educations[idx] = new_edu
		else:
			educations.append(new_edu)
		db.update({"educations": educations}, where("id") == self.parent.current_id)
		self.parent.refresh_edu(educations)
		messagebox.showinfo("提示", "教育经历已保存！")
		self.destroy()

# =========== 社交媒体弹窗 ===========
class SocialDialog(Toplevel):
	def __init__(self, parent, soc=None):
		super().__init__(parent)
		self.parent = parent
		self.soc = soc or {}
		self.title("社交媒体账号")
		self.geometry("450x380")
		self.configure(bg="#2e2e2e")
		center(self)
		self.grab_set()
		self.build()
		self.load()

	def build(self):
		label_pairs = [("平台 *", "platform"), ("账号 *", "account"), ("昵称 *", "nickname"), ("URL", "url"), ("签名", "signature"), ("图片目录", "img_dir")]
		self.vars = {}
		for i, (txt, key) in enumerate(label_pairs):
			Label(self, text=txt, bg="#2e2e2e", fg="#ccc").grid(row=i, column=0, sticky=E, padx=10, pady=4)
			if key == "img_dir":
				dir_frame = Frame(self, bg="#2e2e2e")
				dir_frame.grid(row=i, column=1, sticky=W, padx=10, pady=4)
				var = StringVar()
				Entry(dir_frame, textvariable=var, width=20).pack(side=LEFT)
				Button(dir_frame, text="浏览…", command=lambda: var.set(filedialog.askdirectory() or "")).pack(side=LEFT)
				self.vars[key] = var
			else:
				var = StringVar()
				Entry(self, textvariable=var, width=28).grid(row=i, column=1, sticky=W, padx=10, pady=4)
				self.vars[key] = var
		Button(self, text="确认", bg="#444", fg="#ccc", command=self.ok).grid(row=len(label_pairs), column=0, columnspan=2, pady=10)

	def load(self):
		if self.soc:
			self.vars["platform"].set(self.soc["platform"])
			self.vars["account"].set(self.soc["account"])
			self.vars["nickname"].set(self.soc["nickname"])
			self.vars["url"].set(self.soc.get("url", ""))
			self.vars["signature"].set(self.soc.get("signature", ""))
			self.vars["img_dir"].set(self.soc.get("img_dir", ""))

	def ok(self):
		platform = self.vars["platform"].get().strip()
		account = self.vars["account"].get().strip()
		nickname = self.vars["nickname"].get().strip()
		if not (platform and account and nickname):
			messagebox.showwarning("提示", "平台、账号、昵称为必填项"); return
		new_soc = {
			"platform": platform, "account": account, "nickname": nickname,
			"url": self.vars["url"].get().strip(),
			"signature": self.vars["signature"].get().strip(),
			"img_dir": self.vars["img_dir"].get().strip()
		}
		person = db.get(where("id") == self.parent.current_id)
		socials = person.get("socials", [])
		if self.soc:
			idx = self.soc["index"]
			socials[idx] = new_soc
		else:
			socials.append(new_soc)
		db.update({"socials": socials}, where("id") == self.parent.current_id)
		self.parent.refresh_social(socials)
		messagebox.showinfo("提示", "社交媒体已保存！")
		self.destroy()

# =========== 启动 ===========
if __name__ == "__main__":
	app = MainWindow()
	app.mainloop()
