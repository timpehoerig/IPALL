.PHONY: all src clean

all: src

src:
	$(MAKE) -C src

clean:
	$(MAKE) -C src clean
	rm -f -r ./verify/tmp/
	rm -f -r */tmp_cadicall_negated_models.txt
	rm -f -r ./deltadebug/tmp/