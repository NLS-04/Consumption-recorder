# Major ~~Update~~ Upgrade

At first glance, everything may appear the same, but upon closer inspection, nothing remains as it was. This release marks a significant upgrade for the project, introducing the deployment of an entirely new backend. The transition is notable, shifting from a Windows-exclusive application to a scalable multi-platform one, now supporting *Windows* (with untested but architecturally possible *MacOS* and *Linux* compatibility).

---
## New Additions

- Completely rewrote the console terminal backend, resulting in:
    - Improved interaction, appearance, workflow, and user experience
    - A faster and more reliable interface
    - Multi-platform capability
    - A scalable, maintainable, and less error-prone development environment
- Introduced statistics detailing monthly and yearly readings in both console and PDF output
- Implemented functionality to analyze time spans and export the results to PDF
- Implemented the capability to leave individual entry reading values blank.
- Open PDF files of statistics or analyses in the default browser after generation
- Added an icon to the project and the executable (*with macOS support pending*)
- Included a title for the terminal window


---
## Bug Fixes

- Resolved the problem where a person with a moving_in date in the future and no moving_out date resulted in a negative amount of occupancy months
- Implemented a check that the moving_out date is blank or greater than the moving_in date
- Moved the readings conclusion to a new page to avoid bad page-breaks and improve readability
- Addressed an issue where installing a new meter caused negative extrapolation values of the data

---
## interesting for developers
### New Additions
- Introduced a CHANGELOG.md file for automated releases
- Preliminary logging functionality has been added
- Implemented GitHub actions to automate:
    - Version watermark on the title screen, eliminating the need for manual updates in the code
        > I always forgot to change it in the code so now i don't have to think about it anymore :)
    - Executable build and deployment
    - Publishing releases with changelogs

### Pending TODOs
- last line of first FM disappears iff any data exists, as for now only observed with `manipulate_readings`
- add predictions for the upcoming invoice's compensation payment
- complete invoice
- maybe take this out of this function and let the user choose their own Confirm Frame
- add descriptions to all menu/interaction pages
- de-hard-code main.py by making Console.write_line str's to constant variables and move them to constants.py
- add version-resource-file to .spec
- add option to suppress ctrl-c inputs or to raise an KeyboardInterrupt Exception if not suppressed and pressed
- integrate pynput.keyboard into Key class
- expect ANSI codes to not work properly, assume that it needs refinement in the future when adding fancy ESC styling
- add icon to terminal window
- refactor logging for all files
- add better typing support