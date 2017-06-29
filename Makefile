.PHONY: copy-clad dist examples license wheel vagrant installer

version = $(shell perl -ne '/__version__ = "([^"]+)/ && print $$1;' src/cozmo/version.py)
cladversion = $(shell perl -ne '/__version__ = "([^"]+)/ && print $$1;' ../cozmoclad/src/cozmoclad/__init__.py)

copy-clad:
	rm -rf src/cozmo/_internal/clad/*
	rm -rf src/cozmo/_internal/msgbuffers/*
	cp -r ../../generated/cladPython/clad src/cozmo/_internal/
	cp -r ../message-buffers/support/python/msgbuffers src/cozmo/_internal/


license_targets = src/cozmo/LICENSE.txt examples/LICENSE.txt
example_targets = dist/cozmo_sdk_examples.tar.gz dist/cozmo_sdk_examples.zip

example_filenames = $(shell cd examples && find . -name '*.py' -o -name '*.txt' -o -name '*.png' -o -name '*.md' -o -name '*.json')
example_pathnames = $(shell find examples -name '*.py' -o -name '*.txt' -o -name '*.png' -o -name '*.md' -o -name '*.json')
sdist_filename = dist/cozmo-$(version).tar.gz
wheel_filename = dist/cozmo-$(version)-py3-none-any.whl

license: $(license_targets)

$(license_targets): LICENSE.txt
	for fn in $(license_targets); do \
		cp LICENSE.txt $$fn; \
	done

$(sdist_filename): src/cozmo/LICENSE.txt $(shell find src/cozmo -name '*.py')
	python3 setup.py sdist

$(wheel_filename): src/cozmo/LICENSE.txt $(shell find src/cozmo -name '*.py')
	python3 setup.py bdist_wheel

dist/cozmo_sdk_examples.zip: examples/LICENSE.txt $(example_pathnames)
	rm -f dist/cozmo_sdk_examples.zip dist/cozmo_sdk_examples_$(version).zip
	rm -rf dist/cozmo_sdk_examples_$(version)
	mkdir dist/cozmo_sdk_examples_$(version)
	tar -C examples -c $(example_filenames) | tar -C dist/cozmo_sdk_examples_$(version)  -xv
	cd dist && zip -r cozmo_sdk_examples.zip cozmo_sdk_examples_$(version)
	cd dist && zip -r cozmo_sdk_examples_$(version).zip cozmo_sdk_examples_$(version)

dist/cozmo_sdk_examples.tar.gz: examples/LICENSE.txt $(example_pathnames)
	rm -f dist/cozmo_sdk_examples.tar.gz dist/cozmo_sdk_examples_$(version).tar.gz
	rm -rf dist/cozmo_sdk_examples_$(version)
	mkdir dist/cozmo_sdk_examples_$(version)
	tar -C examples -c $(example_filenames) | tar -C dist/cozmo_sdk_examples_$(version)  -xv
	cd dist && tar -cvzf cozmo_sdk_examples.tar.gz cozmo_sdk_examples_$(version)
	cp -a dist/cozmo_sdk_examples.tar.gz dist/cozmo_sdk_examples_$(version).tar.gz

examples: dist/cozmo_sdk_examples.tar.gz dist/cozmo_sdk_examples.zip

dist/vagrant_bundle.tar.gz: $(sdist_filename) $(example_targets)
	rm -rf dist/vagrant_bundle
	mkdir dist/vagrant_bundle
	cp dist/cozmo_sdk_examples.tar.gz dist/vagrant_bundle/
	cp vagrant/Vagrantfile dist/vagrant_bundle/
	cp vagrant/setup-vm.sh dist/vagrant_bundle/
	cd dist && tar -czvf vagrant_bundle.tar.gz vagrant_bundle
	cp -a dist/vagrant_bundle.tar.gz dist/vagrant_bundle_$(version).tar.gz

dist/vagrant_bundle.zip: dist/vagrant_bundle.tar.gz
	cd dist && zip -r vagrant_bundle.zip vagrant_bundle/
	cp -a dist/vagrant_bundle.zip dist/vagrant_bundle_$(version).zip

vagrant: dist/vagrant_bundle.tar.gz dist/vagrant_bundle.zip

dist: $(sdist_filename) $(wheel_filename) examples vagrant

clad_wheel_filename = dist/cozmoclad-$(cladversion)-py3-none-any.whl
$(clad_wheel_filename):
	make -C ../cozmoclad dist
	cp ../cozmoclad/$(clad_wheel_filename) $(clad_wheel_filename)

installer_filename = sdk_installer_$(version)_clad_$(cladversion)
installer: $(wheel_filename) $(clad_wheel_filename)
	mkdir -p dist/
	mkdir -p dist/$(installer_filename)
	$(shell echo "#!/bin/bash\n\nworking_dir=\"\`dirname \\\"\$$0\\\"\`\"\n\npip3 uninstall -y cozmoclad\npip3 uninstall -y cozmo\npip3 install \"\$$working_dir/$(clad_wheel_filename)\"\npip3 install \"\$$working_dir/$(wheel_filename)\"" > dist/install.sh)
	tar -c $(wheel_filename) $(clad_wheel_filename) | tar -C dist/$(installer_filename) -xv
	mv dist/install.sh dist/$(installer_filename)/install
	chmod +x dist/$(installer_filename)/install
	cd dist && zip -r $(installer_filename).zip $(installer_filename)
	rm -rf dist/$(installer_filename)
