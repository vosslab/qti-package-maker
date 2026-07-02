#!/usr/bin/env python3
"""
Gate A probe kit builder: Canvas Classic Quizzes image import.

Builds two Canvas QTI 1.2 ZIP packages via the real Canvas engine
(qti_package_maker.engines.canvas_qti_v1_2), one per `<img src>` token
variant (plain relative vs `$IMS-CC-FILEBASE$`), so a human can import each
into a Canvas Classic Quizzes sandbox and record which variant actually
resolves the image on import. See docs/MEDIA_LMS_PROBES.md for the import
steps and the results table to fill in.
"""

# Standard Library
import os
import base64
import argparse

# QTI Package Maker
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.engines.canvas_qti_v1_2 import engine_class as canvas_engine

# Bright red 240x120 JPEG with a white border, ~3.6 KB. A real Blackboard
# import discovered that a 1x1-pixel probe figure imports and renders
# perfectly as an invisible dot, which invalidated a day of "image did not
# appear" interpretations; the probe figure must be unmistakably visible
# at a glance, so it is generated at a real size with high-contrast color.
PROBE_JPEG_BYTES = base64.b64decode(
	"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsK"
	"CwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQU"
	"FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAB4APADASIA"
	"AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
	"AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
	"ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
	"p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
	"AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
	"BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK"
	"U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3"
	"uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9U6KK"
	"/PL9qz9qz4p/DX4+eKPDnhzxR/Z2jWX2XyLb+z7WXZvtYZG+Z4mY5Z2PJPX0rz8djqeApqrVTabt"
	"p8/Ndj7DhfhfGcW4yeBwM4xlGLm3NtKycV0jJ3vJdO+p+htFfkz/AMNy/G7/AKHb/wApNj/8Yo/4"
	"bl+N3/Q7f+Umx/8AjFeJ/rJhP5Zfcv8AM/T/APiCvEP/AD/o/wDgU/8A5WfrNRX5M/8ADcvxu/6H"
	"b/yk2P8A8Yo/4bl+N3/Q7f8AlJsf/jFH+smE/ll9y/zD/iCvEP8Az/o/+BT/APlZ+s1Ffkz/AMNy"
	"/G7/AKHb/wApNj/8Yo/4bl+N3/Q7f+Umx/8AjFH+smE/ll9y/wAw/wCIK8Q/8/6P/gU//lZ+s1Ff"
	"kz/w3L8bv+h2/wDKTY//ABij/huX43f9Dt/5SbH/AOMUf6yYT+WX3L/MP+IK8Q/8/wCj/wCBT/8A"
	"lZ+s1Ffkz/w3L8bv+h2/8pNj/wDGKP8AhuX43f8AQ7f+Umx/+MUf6yYT+WX3L/MP+IK8Q/8AP+j/"
	"AOBT/wDlZ+s1Ffkz/wANy/G7/odv/KTY/wDxij/huX43f9Dt/wCUmx/+MUf6yYT+WX3L/MP+IK8Q"
	"/wDP+j/4FP8A+Vn6zUV+TP8Aw3L8bv8Aodv/ACk2P/xij/huX43f9Dt/5SbH/wCMUf6yYT+WX3L/"
	"ADD/AIgrxD/z/o/+BT/+Vn6zUV+TP/Dcvxu/6Hb/AMpNj/8AGKP+G5fjd/0O3/lJsf8A4xR/rJhP"
	"5Zfcv8w/4grxD/z/AKP/AIFP/wCVn6zUV+TP/Dcvxu/6Hb/yk2P/AMYo/wCG5fjd/wBDt/5SbH/4"
	"xR/rJhP5Zfcv8w/4grxD/wA/6P8A4FP/AOVn6zUV+TP/AA3L8bv+h2/8pNj/APGKP+G5fjd/0O3/"
	"AJSbH/4xR/rJhP5Zfcv8w/4grxD/AM/6P/gU/wD5WfrNRX5M/wDDcvxu/wCh2/8AKTY//GKP+G5f"
	"jd/0O3/lJsf/AIxR/rJhP5Zfcv8AMP8AiCvEP/P+j/4FP/5WfrNRX5M/8Ny/G7/odv8Ayk2P/wAY"
	"o/4bl+N3/Q7f+Umx/wDjFH+smE/ll9y/zD/iCvEP/P8Ao/8AgU//AJWfrNRX5M/8Ny/G7/odv/KT"
	"Y/8Axij/AIbl+N3/AEO3/lJsf/jFH+smE/ll9y/zD/iCvEP/AD/o/wDgU/8A5WfrNRX55fsp/tWf"
	"FP4lfHzwv4c8R+KP7R0a9+1efbf2faxb9lrNIvzJErDDIp4I6elfobXt4HHU8fTdWkmknbX5eb7n"
	"5hxRwvjOEsZDA46cZSlFTTg21ZuS6xi73i+nbUK/Jn9uX/k6Xxt/25f+kNvX6zV+TP7cv/J0vjb/"
	"ALcv/SG3rxOJP90j/iX5M/T/AAV/5KGv/wBeZf8ApdM8Hooor83P7UCiiigAooooAKKKKACiiigA"
	"ooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAPeP2Gv+TpfBP8A2+/+kNxX6zV+TP7DX/J0"
	"vgn/ALff/SG4r9Zq/SOG/wDdJf4n+SP4r8av+Shof9eY/wDpdQK/Jn9uX/k6Xxt/25f+kNvX6zV+"
	"TP7cv/J0vjb/ALcv/SG3o4k/3SP+Jfkw8Ff+Shr/APXmX/pdM8Hooor83P7UCiiigAooooAKKKKA"
	"CiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAPeP2Gv8Ak6XwT/2+/wDpDcV+s1fk"
	"z+w1/wAnS+Cf+33/ANIbiv1mr9I4b/3SX+J/kj+K/Gr/AJKGh/15j/6XUCvyZ/bl/wCTpfG3/bl/"
	"6Q29frNX5M/ty/8AJ0vjb/ty/wDSG3o4k/3SP+Jfkw8Ff+Shr/8AXmX/AKXTPB6KKK/Nz+1Aoooo"
	"AKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigD3j9hr/k6XwT/ANvv"
	"/pDcV+s1fkz+w1/ydL4J/wC33/0huK/Wav0jhv8A3SX+J/kj+K/Gr/koaH/XmP8A6XUCvyZ/bl/5"
	"Ol8bf9uX/pDb1+s1fkz+3L/ydL42/wC3L/0ht6OJP90j/iX5MPBX/koa/wD15l/6XTPB6KKK/Nz+"
	"1AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigD3j9hr/AJOl"
	"8E/9vv8A6Q3FfrNX5M/sNf8AJ0vgn/t9/wDSG4r9Zq/SOG/90l/if5I/ivxq/wCShof9eY/+l1Ar"
	"8mf25f8Ak6Xxt/25f+kNvX6zV+TP7cv/ACdL42/7cv8A0ht6OJP90j/iX5MPBX/koa//AF5l/wCl"
	"0zweiiivzc/tQKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoooo"
	"A94/Ya/5Ol8E/wDb7/6Q3FfrNX5M/sNf8nS+Cf8At9/9Ibiv1mr9I4b/AN0l/if5I/ivxq/5KGh/"
	"15j/AOl1Ar8mf25f+TpfG3/bl/6Q29frNX55ftWfsp/FP4lfHzxR4j8OeF/7R0a9+y+Rc/2haxb9"
	"lrDG3yvKrDDIw5A6ela8QUalbCxjSi5PmWyv0Z5/hFmODy3Pa1bHVo0oujJJzkoq/PTdrtpXsm7e"
	"TPi6iveP+GGvjd/0JP8A5VrH/wCP0f8ADDXxu/6En/yrWP8A8fr4H6hi/wDnzL/wF/5H9c/62cPf"
	"9DGj/wCDYf8AyR4PRXvH/DDXxu/6En/yrWP/AMfo/wCGGvjd/wBCT/5VrH/4/R9Qxf8Az5l/4C/8"
	"g/1s4e/6GNH/AMGw/wDkjweiveP+GGvjd/0JP/lWsf8A4/R/ww18bv8AoSf/ACrWP/x+j6hi/wDn"
	"zL/wF/5B/rZw9/0MaP8A4Nh/8keD0V7x/wAMNfG7/oSf/KtY/wDx+j/hhr43f9CT/wCVax/+P0fU"
	"MX/z5l/4C/8AIP8AWzh7/oY0f/BsP/kjweiveP8Ahhr43f8AQk/+Vax/+P0f8MNfG7/oSf8AyrWP"
	"/wAfo+oYv/nzL/wF/wCQf62cPf8AQxo/+DYf/JHg9Fe8f8MNfG7/AKEn/wAq1j/8fo/4Ya+N3/Qk"
	"/wDlWsf/AI/R9Qxf/PmX/gL/AMg/1s4e/wChjR/8Gw/+SPB6K94/4Ya+N3/Qk/8AlWsf/j9H/DDX"
	"xu/6En/yrWP/AMfo+oYv/nzL/wABf+Qf62cPf9DGj/4Nh/8AJHg9Fe8f8MNfG7/oSf8AyrWP/wAf"
	"o/4Ya+N3/Qk/+Vax/wDj9H1DF/8APmX/AIC/8g/1s4e/6GNH/wAGw/8AkjweiveP+GGvjd/0JP8A"
	"5VrH/wCP0f8ADDXxu/6En/yrWP8A8fo+oYv/AJ8y/wDAX/kH+tnD3/Qxo/8Ag2H/AMkeD0V7x/ww"
	"18bv+hJ/8q1j/wDH6P8Ahhr43f8AQk/+Vax/+P0fUMX/AM+Zf+Av/IP9bOHv+hjR/wDBsP8A5I8H"
	"or3j/hhr43f9CT/5VrH/AOP0f8MNfG7/AKEn/wAq1j/8fo+oYv8A58y/8Bf+Qf62cPf9DGj/AODY"
	"f/JHg9Fe8f8ADDXxu/6En/yrWP8A8fo/4Ya+N3/Qk/8AlWsf/j9H1DF/8+Zf+Av/ACD/AFs4e/6G"
	"NH/wbD/5I8Hor3j/AIYa+N3/AEJP/lWsf/j9H/DDXxu/6En/AMq1j/8AH6PqGL/58y/8Bf8AkH+t"
	"nD3/AEMaP/g2H/yQfsNf8nS+Cf8At9/9Ibiv1mr88v2U/wBlP4p/DX4+eF/EfiPwv/Z2jWX2rz7n"
	"+0LWXZvtZo1+VJWY5Z1HAPX0r9Da++4fo1KOFlGrFxfM91boj+RvF3McHmWe0a2BrRqxVGKbhJSV"
	"+eo7XTavZp280FFFFfTH4gFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFAB"
	"RRRQAUUUUAFFFFABRRRQB//Z"
)

PROBE_MEDIA_FILENAME = "probe-figure.jpg"
PROBE_QUESTION_TEXT = (
	f'What color is this image? <img src="images/{PROBE_MEDIA_FILENAME}" alt="probe figure"/>'
)
PROBE_CHOICES = ["Red", "Blue"]
PROBE_ANSWER = "Red"


#============================================
def build_probe_bank() -> ItemBank:
	"""
	Build a tiny image-bearing item bank for the Canvas gate A probe.

	The probe JPEG bytes are spilled into a bank-owned temp dir via
	add_image() rather than a persistent media dir beside the ZIPs; the
	caller is responsible for calling cleanup() once every ZIP that consumes
	this bank has been written.

	Returns:
		ItemBank: one multiple-choice item referencing the staged image.
	"""
	bank = ItemBank()
	bank.add_image(f"images/{PROBE_MEDIA_FILENAME}", PROBE_JPEG_BYTES)
	bank.add_item("MC", (PROBE_QUESTION_TEXT, PROBE_CHOICES, PROBE_ANSWER))
	return bank


#============================================
def build_probe_kit(output_dir: str) -> dict:
	"""
	Build both Canvas `<img src>` token probe ZIPs (gate A).

	Args:
		output_dir: directory to stage the probe media and write the ZIPs into.

	Returns:
		dict[str, str]: variant name ("relative", "filebase") -> written ZIP path.
	"""
	os.makedirs(output_dir, exist_ok=True)
	# One bank feeds both variants below; cleanup() runs once, after both
	# saves have consumed it.
	bank = build_probe_bank()

	kit_paths = {}

	relative_engine = canvas_engine.EngineClass(
		"canvas_probe_relative", verbose=False,
		canvas_src_variant=canvas_engine.CANVAS_SRC_VARIANT_RELATIVE,
	)
	relative_outfile = os.path.join(output_dir, "canvas_probe_relative.zip")
	kit_paths["relative"] = relative_engine.save_package(bank, outfile=relative_outfile)

	filebase_engine = canvas_engine.EngineClass(
		"canvas_probe_filebase", verbose=False,
		canvas_src_variant=canvas_engine.CANVAS_SRC_VARIANT_FILEBASE,
	)
	filebase_outfile = os.path.join(output_dir, "canvas_probe_filebase.zip")
	kit_paths["filebase"] = filebase_engine.save_package(bank, outfile=filebase_outfile)

	bank.cleanup()
	return kit_paths


#============================================
def parse_args() -> argparse.Namespace:
	"""
	Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Build the Canvas image-import probe kit (gate A)."
	)
	parser.add_argument(
		'-o', '--output-dir', dest='output_dir', default='output_probes/canvas',
		help="Directory to write the probe ZIPs into.",
	)
	args = parser.parse_args()
	return args


#============================================
def main() -> None:
	args = parse_args()
	kit_paths = build_probe_kit(args.output_dir)
	for variant_name in sorted(kit_paths):
		print(f"Wrote {variant_name} probe kit: {kit_paths[variant_name]}")


#============================================
if __name__ == '__main__':
	main()
