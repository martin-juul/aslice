// SPDX-License-Identifier: Apache-2.0
// One visible input/action probe and a separate document-mode executable.
#import <Cocoa/Cocoa.h>

@interface Probe : NSObject <NSApplicationDelegate>
@property(strong) NSWindow* window;
@property(strong) NSTextField* input;
@property(strong) NSTextField* result;
@end

@implementation Probe

- (void)applicationDidFinishLaunching:(NSNotification*)notification {
    (void)notification;
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(80, 80, 500, 220)
                                              styleMask:(NSTitledWindowMask | NSClosableWindowMask)
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    self.window.title = @"Darwin compatibility application probe";
    self.input = [[NSTextField alloc] initWithFrame:NSMakeRect(20, 150, 450, 24)];
    self.input.stringValue = @"Type a unique test value";
    [self.window.contentView addSubview:self.input];
    self.result = [[NSTextField alloc] initWithFrame:NSMakeRect(20, 110, 450, 24)];
    self.result.editable = NO;
    [self.window.contentView addSubview:self.result];
    NSArray* titles = @[ @"Apply", @"Open", @"Save" ];
    SEL actions[] = {@selector(apply:), @selector(open:), @selector(save:)};
    for (NSUInteger i = 0; i < (DOCUMENT ? 3 : 1); ++i) {
        NSButton* button = [[NSButton alloc] initWithFrame:NSMakeRect(20 + i * 150, 40, 130, 30)];
        button.title = titles[i];
        button.target = self;
        button.action = actions[i];
        [self.window.contentView addSubview:button];
    }
    NSMenu* menu = [[NSMenu alloc] initWithTitle:@"Main"];
    NSMenuItem* root = [[NSMenuItem alloc] initWithTitle:@"Probe" action:NULL keyEquivalent:@""];
    NSMenu* application = [[NSMenu alloc] initWithTitle:@"Probe"];
    NSMenuItem* apply = [[NSMenuItem alloc] initWithTitle:@"Apply"
                                                   action:@selector(apply:)
                                            keyEquivalent:@"a"];
    apply.target = self;
    [application addItem:apply];
    [application addItemWithTitle:@"Quit" action:@selector(terminate:) keyEquivalent:@"q"];
    root.submenu = application;
    [menu addItem:root];
    NSApp.mainMenu = menu;
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)apply:(id)sender {
    (void)sender;
    self.result.stringValue = self.input.stringValue;
}

- (void)save:(id)sender {
    (void)sender;
    NSSavePanel* panel = [NSSavePanel savePanel];
    if ([panel runModal] == NSModalResponseOK) {
        NSError* error = nil;
        BOOL saved = [self.input.stringValue writeToURL:panel.URL
                                             atomically:YES
                                               encoding:NSUTF8StringEncoding
                                                  error:&error];
        self.result.stringValue = saved ? @"Saved" : error.localizedDescription;
    }
}

- (void)open:(id)sender {
    (void)sender;
    NSOpenPanel* panel = [NSOpenPanel openPanel];
    if ([panel runModal] == NSModalResponseOK) {
        NSError* error = nil;
        NSString* text = [NSString stringWithContentsOfURL:panel.URL
                                                  encoding:NSUTF8StringEncoding
                                                     error:&error];
        if (text) {
            self.input.stringValue = text;
            self.result.stringValue = @"Opened";
        } else {
            self.result.stringValue = error.localizedDescription;
        }
    }
}

@end

int main(void) {
    @autoreleasepool {
        NSApplication* app = [NSApplication sharedApplication];
        Probe* delegate = [Probe new];
        app.delegate = delegate;
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        [app run];
    }
    return 0;
}
