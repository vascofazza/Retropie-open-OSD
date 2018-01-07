TARGETS=osd/lib \
osd

default :all

all:
	for target in $(TARGETS); do ($(MAKE) -C $$target); done

clean:
	for target in $(TARGETS); do ($(MAKE) -C $$target clean); done

