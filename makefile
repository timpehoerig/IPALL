.PHONY: all src clean

all: src

src:
	$(MAKE) -C src

clean:
	$(MAKE) -C src clean
	rm -f -r ./verify/tmp/
