# Standard Library
import os

# QTI Package Maker
import qti_package_maker.package_interface


def test_canvas_output(tmp_cwd):
	qti_packer = qti_package_maker.package_interface.QTIPackageInterface("dummy", allow_mixed=True)
	qti_packer.show_available_item_types()
	question_text = "What is your favorite color?"
	answer_text = "blue"
	choices_list = ["blue", "red", "yellow"]
	qti_packer.add_item("MC", (question_text, choices_list, answer_text))

	question_text = "Which are types of fruit?"
	answers_list = ["orange", "banana", "apple"]
	choices_list = ["orange", "banana", "apple", "lettuce", "spinach"]
	qti_packer.add_item("MA", (question_text, choices_list, answers_list))

	question_text = "Match item to color."
	prompts_list = ["orange", "banana", "lettuce"]
	choices_list = ["orange", "yellow", "green", "distractor"]
	qti_packer.add_item("MATCH", (question_text, prompts_list, choices_list))

	output_file = qti_packer.save_package("canvas")
	assert output_file
	assert os.path.exists(output_file)
