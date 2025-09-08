# frozen_string_literal: true

################################################################################
# Style file for markdownlint.
#
# https://github.com/markdownlint/markdownlint/blob/master/docs/configuration.md
#
# This file is referenced by the project `.mdlrc`.
################################################################################

#===============================================================================
# Start with all built-in rules.
# https://github.com/markdownlint/markdownlint/blob/master/docs/RULES.md
all

#===============================================================================
# Override default parameters for some built-in rules.
# https://github.com/markdownlint/markdownlint/blob/master/docs/creating_styles.md#parameters

exclude_rule 'MD001' # Header levels should only increment by one level at a time
exclude_rule 'MD004' # Unordered list style
exclude_rule 'MD007' # Unordered list indentation
exclude_rule 'MD029' # Ordered list item prefix
exclude_rule 'MD013' # Line length
exclude_rule 'MD031' # Fenced code blocks should be surrounded by blank lines
exclude_rule 'MD033' # Inline HTML
exclude_rule 'MD034' # Bare URL used
exclude_rule 'MD041' # First line in file should be a top level header
